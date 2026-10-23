"""
Tests pytest du pipeline bout-en-bout — TP 13.

Le pipeline tourne une seule fois par session sur l'échantillon partagé, dans un dossier
temporaire, sans base PostgreSQL (l'étape `load_database` doit alors être ignorée avec
un avertissement). Les tests vérifient que chaque étape produit ce qu'elle annonce,
qu'une étape relancée ne change aucun octet, qu'une étape sans entrée échoue avec un
message utile, que le split est stratifié, reproductible et figé, et que le schéma décrit
exactement le fichier écrit.
"""

import json
import shutil
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from nutriscope.options import CONFIG, RANDOM_SEED, ROOT_PATH, TEST_SIZE
from nutriscope.pipeline import (
    CLEAN,
    DB_PASSWORD_ENV,
    DB_PASSWORD_FILE_ENV,
    EXPORT,
    FAILED,
    JOURNAL,
    OK,
    PARQUET,
    RAW,
    SKIPPED,
    STEPS,
    Pipeline,
    main,
    purge,
    relative_message,
    source_name,
)
from nutriscope.storage.convert_parquet import SUCCESS_MARKER
from nutriscope.storage.export_features import SPLIT, TARGET, TEST, TRAIN, assign_split, sha256

SAMPLE_PATH = ROOT_PATH / "data-nutriscope" / "echantillon_france.csv"
RUN_DATE = date(2026, 10, 14)
TAG = "20261014"


def make_pipeline(data_dir: Path, **kwargs) -> Pipeline:
    """Pipeline sur l'échantillon, sans base ni sortie console."""
    options = {"source": SAMPLE_PATH, "data_dir": data_dir, "run_date": RUN_DATE,
               "db_password_file": data_dir / "no_password.txt", "verbose": False}
    return Pipeline(**{**options, **kwargs})


def tree_hashes(path: Path) -> dict[str, str]:
    """Empreinte de chaque fichier d'un dossier (ou d'un fichier seul)."""
    if path.is_file():
        return {path.name: sha256(path)}
    return {file.relative_to(path).as_posix(): sha256(file) for file in sorted(path.rglob("*")) if file.is_file()}


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    """Aucun identifiant PostgreSQL ne fuit de l'environnement du poste dans les tests."""
    monkeypatch.delenv(DB_PASSWORD_ENV, raising=False)
    monkeypatch.delenv(DB_PASSWORD_FILE_ENV, raising=False)


@pytest.fixture(scope="session")
def run(tmp_path_factory):
    """Le pipeline complet, exécuté une fois sur l'échantillon."""
    if not SAMPLE_PATH.exists():
        pytest.skip(f"Échantillon absent : {SAMPLE_PATH}")
    with pytest.MonkeyPatch.context() as patch:
        patch.delenv(DB_PASSWORD_ENV, raising=False)
        patch.delenv(DB_PASSWORD_FILE_ENV, raising=False)
        pipeline = make_pipeline(tmp_path_factory.mktemp("data"))
        results = {result.step: result for result in pipeline.run_all()}
    return pipeline, results


@pytest.fixture(scope="session")
def export_df(run) -> pd.DataFrame:
    pipeline, _ = run
    return pd.read_parquet(pipeline.dated(EXPORT))


@pytest.fixture(scope="session")
def contract(run) -> dict:
    pipeline, _ = run
    return json.loads(pipeline.dated(EXPORT).with_suffix(".schema.json").read_text(encoding="utf-8"))


# ============================================================================
# CHAQUE ÉTAPE PRODUIT CE QU'ELLE ANNONCE
# ============================================================================

def test_all_steps_run_and_database_is_skipped_with_warning(run):
    _, results = run
    assert list(results) == list(STEPS)
    assert {step: result.status for step, result in results.items()} == {
        "load": OK, "clean_data": OK, "load_database": SKIPPED, "parquet": OK, "exports": OK,
    }
    assert results["load_database"].message.startswith("WARNING")


def test_each_step_writes_dated_outputs(run):
    pipeline, _ = run
    data = pipeline.data_dir / "echantillon_france"          # un dossier par source
    expected = [
        data / "raw" / f"products_raw_{TAG}.parquet",
        data / "raw" / f"products_raw_{TAG}.manifest.json",
        data / "clean" / f"products_clean_{TAG}.parquet",
        data / "clean" / f"cleaning_report_{TAG}.md",
        data / "clean" / f"cleaning_rules_{TAG}.json",
        data / "parquet" / f"products_{TAG}" / SUCCESS_MARKER,
        data / "parquet" / f"products_{TAG}.schema.json",
        data / "exports" / f"features_nutriscore_{TAG}.parquet",
        data / "exports" / f"features_nutriscore_{TAG}.schema.json",
    ]
    assert [path for path in expected if not path.exists()] == []


def test_load_keeps_barcodes_as_text_and_fingerprints_source(run):
    pipeline, results = run
    raw = pd.read_parquet(pipeline.dated(RAW))
    assert pd.api.types.is_string_dtype(raw["code"])
    manifest = json.loads(pipeline.dated(RAW).with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_fingerprint"] == {"method": "sha256", "value": sha256(SAMPLE_PATH),
                                              "bytes": SAMPLE_PATH.stat().st_size}
    assert manifest["rows"] == results["load"].rows == len(raw)
    assert manifest["versions"]["duckdb"]
    assert "ODbL" in manifest["license"]


def test_load_keeps_only_configured_columns_all_as_text(run):
    pipeline, _ = run
    raw = pd.read_parquet(pipeline.dated(RAW))
    manifest = json.loads(pipeline.dated(RAW).with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert list(raw.columns) == manifest["columns"]
    assert set(raw.columns) <= set(CONFIG["columns"])
    assert all(pd.api.types.is_string_dtype(raw[column]) for column in raw.columns)   # typage : règle 1 du TP 9


def test_parquet_counts_the_same_products_as_the_cleaned_dataset(run):
    pipeline, results = run
    assert results["parquet"].rows == results["clean_data"].rows == len(pd.read_parquet(pipeline.dated(CLEAN)))


def test_journal_has_one_line_per_step(run):
    pipeline, _ = run
    lines = [json.loads(line) for line in (pipeline.data_dir / JOURNAL).read_text(encoding="utf-8").splitlines()]
    first_run = lines[:len(STEPS)]
    assert [line["step"] for line in first_run] == list(STEPS)
    assert all({"timestamp", "duration_s", "status", "rows"} <= set(line) for line in first_run)
    assert len({line["run_id"] for line in first_run}) == 1            # une exécution, un identifiant
    assert {line["source"] for line in first_run} == {"data-nutriscope/echantillon_france.csv"}
    assert first_run[0]["options"] == {"batches": "auto", "memory": None, "force": False}
    assert {line["name"] for line in first_run} == {"echantillon_france"}


def test_journal_messages_carry_no_absolute_repository_path():
    absolute = ROOT_PATH.resolve() / "data" / "exports" / "features.parquet"
    assert relative_message(f"{absolute} already exists") == "data/exports/features.parquet already exists" \
        or relative_message(f"{absolute} already exists") == "data\\exports\\features.parquet already exists"
    assert str(ROOT_PATH.resolve()) not in relative_message(f"FileExistsError: {absolute}")


# ============================================================================
# IDEMPOTENCE ET REPRISE
# ============================================================================

def test_rerunning_parquet_changes_no_byte(run):
    pipeline, _ = run
    folder = pipeline.dated(PARQUET)
    schema_path = folder.with_name(f"{folder.name}.schema.json")
    before = {**tree_hashes(folder), **tree_hashes(schema_path)}
    assert pipeline.run("parquet").status == OK
    assert {**tree_hashes(folder), **tree_hashes(schema_path)} == before


def test_rerunning_load_and_clean_changes_no_data_byte(run):
    pipeline, _ = run
    before = (sha256(pipeline.dated(RAW)), sha256(pipeline.dated(CLEAN)))
    assert pipeline.run("load").status == OK
    assert pipeline.run("clean_data").status == OK
    assert (sha256(pipeline.dated(RAW)), sha256(pipeline.dated(CLEAN))) == before


def test_exports_alone_finds_the_previous_day_parquet(run, tmp_path):
    pipeline, _ = run
    shutil.copytree(pipeline.output_dir / "parquet", tmp_path / pipeline.name / "parquet")  # exports/ effacé
    next_day = make_pipeline(tmp_path, run_date=RUN_DATE + timedelta(days=1))
    result = next_day.run("exports")
    assert result.status == OK, result.message
    assert next_day.dated(EXPORT).name == "features_nutriscore_20261015.parquet"


def test_step_without_input_fails_with_a_useful_message(tmp_path):
    pipeline = make_pipeline(tmp_path)
    for step, previous in [("clean_data", "load"), ("parquet", "clean_data"), ("exports", "parquet")]:
        result = pipeline.run(step)
        assert result.status == FAILED
        assert f"`{previous}`" in result.message
    journal = (tmp_path / JOURNAL).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["status"] for line in journal] == [FAILED] * 3   # les échecs sont journalisés


def test_exports_refuses_an_interrupted_parquet(run, tmp_path):
    pipeline, _ = run
    shutil.copytree(pipeline.output_dir / "parquet", tmp_path / pipeline.name / "parquet")
    (tmp_path / pipeline.name / "parquet" / f"products_{TAG}" / SUCCESS_MARKER).unlink()
    result = make_pipeline(tmp_path).run("exports")
    assert result.status == FAILED
    assert "_SUCCESS" in result.message


def test_missing_source_fails_with_a_useful_message(tmp_path):
    result = make_pipeline(tmp_path, source=tmp_path / "absent.csv").run("load")
    assert result.status == FAILED
    assert "--source" in result.message


def test_database_required_fails_without_credentials(run):
    pipeline, _ = run
    strict = make_pipeline(pipeline.data_dir, require_db=True)
    assert strict.run("load_database").status == FAILED


# ============================================================================
# NETTOYAGE PAR LOTS (gros volumes)
# ============================================================================

def test_batched_cleaning_gives_the_same_dataset(run, tmp_path):
    """Nettoyer en 3 lots (répartis par code-barres) donne exactement le nettoyé en un bloc."""
    pipeline, _ = run
    shutil.copytree(pipeline.output_dir / "raw", tmp_path / pipeline.name / "raw")
    batched = make_pipeline(tmp_path, batches=3)
    result = batched.run("clean_data")
    assert result.status == OK, result.message
    assert "3 batch" in result.message
    pd.testing.assert_frame_equal(pd.read_parquet(batched.dated(CLEAN)), pd.read_parquet(pipeline.dated(CLEAN)))

    def totals(p):
        rules = json.loads(p.dated(CLEAN).with_name(f"cleaning_rules_{TAG}.json").read_text(encoding="utf-8"))
        return [(r["rule"], r["lines_before"], r["lines_after"], r["lines_changed"]) for r in rules["rules"]]

    assert totals(batched) == totals(pipeline)                 # comptes rendus additionnés à l'identique
    assert not (batched.output_dir / "tmp" / f"clean_batches_{TAG}").exists()   # lots temporaires effacés


def test_single_block_below_one_million_rows(run):
    pipeline, _ = run
    rules = json.loads(pipeline.dated(CLEAN).with_name(f"cleaning_rules_{TAG}.json").read_text(encoding="utf-8"))
    assert rules["batches"] == 1


# ============================================================================
# SPLIT FIGÉ
# ============================================================================

def test_split_is_stratified_on_the_grade(export_df):
    test_share = export_df.groupby(TARGET)[SPLIT].apply(lambda split: (split == TEST).mean())
    assert len(test_share) == 5
    assert test_share.between(TEST_SIZE - 0.01, TEST_SIZE + 0.01).all(), test_share


def test_split_is_reproducible_product_by_product(export_df):
    shuffled = export_df.sample(frac=1, random_state=0)
    again = assign_split(shuffled["code"], shuffled[TARGET])
    assert again.reindex(export_df.index).tolist() == export_df[SPLIT].tolist()


def test_export_is_frozen_and_force_gives_the_same_sha256(run):
    pipeline, _ = run
    path = pipeline.dated(EXPORT)
    before = sha256(path)
    refused = pipeline.run("exports")
    assert refused.status == FAILED and "FileExistsError" in refused.message
    forced = make_pipeline(pipeline.data_dir, force=True).run("exports")
    assert forced.status == OK
    assert sha256(path) == before


def test_schema_describes_the_written_file(export_df, contract, run):
    pipeline, _ = run
    assert contract["sha256"] == sha256(pipeline.dated(EXPORT))
    assert contract["row_count"] == len(export_df)
    assert [column["name"] for column in contract["columns"]] == list(export_df.columns)
    split = contract["split"]
    assert split["seed"] == RANDOM_SEED == 42
    assert split["test_size"] == TEST_SIZE
    counts = export_df.groupby([TARGET, SPLIT]).size()
    for grade, entry in split["counts_by_grade"].items():
        assert entry[TRAIN] == counts.get((grade, TRAIN), 0)
        assert entry[TEST] == counts.get((grade, TEST), 0)
    assert "fit" in split["usage_rule"]
    assert {"code", "nutriscore_score", "split"} <= set(contract["forbidden_features"])
    assert contract["git_commit"]


# ============================================================================
# CLI ET PURGE
# ============================================================================

def _touch(paths):
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")


def test_output_folder_is_named_after_the_source(tmp_path):
    assert source_name(Path("data/en.openfoodfacts.org.products.csv")) == "en-openfoodfacts-org-products"
    assert source_name(SAMPLE_PATH) == "echantillon_france"
    assert make_pipeline(tmp_path).output_dir == tmp_path / "echantillon_france"
    assert make_pipeline(tmp_path, name="essai").output_dir == tmp_path / "essai"
    for invalid in ("logs", "raw", "Avec Espace"):
        with pytest.raises(ValueError):
            make_pipeline(tmp_path, name=invalid)


def test_two_sources_never_overwrite_each_other(run, tmp_path):
    """Le même jour, une autre source écrit dans son propre dossier : l'export figé de l'échantillon ne la bloque pas."""
    pipeline, _ = run
    other = make_pipeline(pipeline.data_dir, name="autre_source")
    before = sha256(pipeline.dated(EXPORT))
    assert other.run("load").status == OK
    assert other.dated(RAW).parent.parent == pipeline.data_dir / "autre_source"
    assert sha256(pipeline.dated(EXPORT)) == before


def test_purge_removes_only_dated_outputs_of_the_current_source(tmp_path):
    kept = [tmp_path / "en.openfoodfacts.org.products.csv",
            tmp_path / "echantillon_france" / "clean" / "notes.csv",
            tmp_path / "echantillon_france" / "exports" / f"features_nutriscore_{TAG}.parquet",
            tmp_path / "autre" / "raw" / f"products_raw_{TAG}.parquet",          # autre source
            tmp_path / JOURNAL]
    removed = [tmp_path / "echantillon_france" / "raw" / f"products_raw_{TAG}.parquet",
               tmp_path / "echantillon_france" / "clean" / f"products_clean_{TAG}.parquet",
               tmp_path / "echantillon_france" / "parquet" / f"products_{TAG}" / SUCCESS_MARKER,
               tmp_path / "echantillon_france" / "tmp" / "duckdb" / "spill.tmp"]
    _touch(kept + removed)
    purge(tmp_path, name="echantillon_france")
    assert all(path.exists() for path in kept)
    assert not any(path.exists() for path in removed)
    assert not (tmp_path / "echantillon_france" / "parquet" / f"products_{TAG}").exists()


def test_purge_all_covers_every_source_and_the_old_layout(tmp_path):
    kept = [tmp_path / "en.openfoodfacts.org.products.csv",
            tmp_path / "clean" / "en.openfoodfacts.org.products.csv",            # source non datée
            tmp_path / "autre" / "exports" / f"features_nutriscore_{TAG}.parquet",
            tmp_path / JOURNAL]
    removed = [tmp_path / "echantillon_france" / "raw" / f"products_raw_{TAG}.parquet",
               tmp_path / "autre" / "clean" / f"products_clean_{TAG}.parquet",
               tmp_path / "raw" / f"products_raw_{TAG}.parquet",                 # ancienne organisation
               tmp_path / "tmp" / "duckdb" / "spill.tmp"]
    _touch(kept + removed)
    assert main(["purge", "-a", "--data-dir", str(tmp_path)]) == 0
    assert all(path.exists() for path in kept)
    assert not any(path.exists() for path in removed)
    assert main(["purge", "-a", "--include-exports", "--data-dir", str(tmp_path)]) == 0
    assert not kept[2].exists()


def test_all_flag_is_reserved_to_purge():
    with pytest.raises(SystemExit) as error:
        main(["all", "-a"])
    assert error.value.code == 2


def test_cli_rejects_unknown_step():
    with pytest.raises(SystemExit) as error:
        main(["bogus"])
    assert error.value.code == 2


def test_cli_accepts_the_brief_step_names(tmp_path):
    # `nettoyer` = `clean_data` : échoue proprement (pas de brut), code de retour 1
    assert main(["nettoyer", "--data-dir", str(tmp_path), "--date", TAG]) == 1
