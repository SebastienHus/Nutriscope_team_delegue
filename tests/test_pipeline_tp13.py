"""
Tests du pipeline bout-en-bout — TP 13.

Toujours sur l'ÉCHANTILLON partagé (data-nutriscope/echantillon_france.csv), dans des dossiers
temporaires : jamais sur data/ ni sur le fichier complet. Le pipeline est exécuté une fois par session
(fixture `run`), puis chaque test vérifie une promesse de l'énoncé.

Les tests PostgreSQL réels ne tournent que si NUTRISCOPE_TEST_DB=1 et DB_PASSWORD sont définis.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

duckdb = pytest.importorskip("duckdb")
pd = pytest.importorskip("pandas")

from nutriscope import journal  # noqa: E402
from nutriscope.config import DEFAULT_SOURCE, Settings, detect_separator, parse_date  # noqa: E402
from nutriscope.files import SUCCESS, sha256_file, tree_hashes  # noqa: E402
from nutriscope.steps import charger, charger_base, exports, nettoyer, parquet  # noqa: E402
from nutriscope.steps.base import run_step  # noqa: E402

RUN_DATE = date(2026, 10, 14)


def make_settings(data_dir: Path, **overrides) -> Settings:
    values = dict(data_dir=data_dir, source=DEFAULT_SOURCE, run_date=RUN_DATE, batches=4,
                  duckdb_memory="2GB", skip=(), db_password=None)
    values.update(overrides)
    settings = Settings.from_env(**{k: v for k, v in values.items() if k != "db_password"})
    from dataclasses import replace
    return replace(settings, db_password=overrides.get("db_password"))


@pytest.fixture(scope="session")
def run(tmp_path_factory):
    """Exécute charger → nettoyer → parquet → exports une fois (sans base) et rend les résultats."""
    if not DEFAULT_SOURCE.is_file():
        pytest.skip(f"Échantillon absent : {DEFAULT_SOURCE}")
    settings = make_settings(tmp_path_factory.mktemp("data"))
    results = {name: run_step(name, module.run, settings)
               for name, module in (("charger", charger), ("nettoyer", nettoyer),
                                    ("parquet", parquet), ("exports", exports))}
    for name, result in results.items():
        assert result.status == "ok", f"{name} : {result.message}"
    return settings, results


def export_frame(settings) -> "pd.DataFrame":
    path, _ = exports.output_paths(settings)
    return pd.read_parquet(path)


# ------------------------------------------------------------------ configuration (sans données)

def test_separateur_detecte(tmp_path):
    csv = tmp_path / "a.csv"
    csv.write_text("code,product_name\n1,x\n", encoding="utf-8")
    tsv = tmp_path / "b.csv"
    tsv.write_text("code\tproduct_name\tbrands\n1\tx\ty\n", encoding="utf-8")
    assert detect_separator(csv) == "," and detect_separator(tsv) == "\t"


def test_date_et_dossiers(tmp_path):
    settings = make_settings(tmp_path)
    assert parse_date("2026-10-14") == RUN_DATE and settings.stamp == "20261014"
    assert settings.raw_dir == tmp_path / "raw" and settings.exports_dir == tmp_path / "exports"


# ------------------------------------------------------------------ charger

def test_charger_produit_brut_et_manifeste(run):
    settings, results = run
    out = charger.output_path(settings)
    assert out.is_file() and out.with_name(out.stem + ".manifest.json").is_file()
    codes = pd.read_parquet(out, columns=["code"])["code"].dropna()
    assert results["charger"].rows >= len(codes) > 0
    assert codes.map(type).eq(str).all()                     # code-barres en texte
    assert codes.str.startswith("0").any()                   # zéros de tête conservés


def test_charger_idempotent(run, tmp_path):
    settings, _ = run
    other = make_settings(tmp_path)
    assert run_step("charger", charger.run, other).status == "ok"
    assert sha256_file(charger.output_path(other)) == sha256_file(charger.output_path(settings))


# ------------------------------------------------------------------ nettoyer

def test_nettoyer_produit_nettoye_rapport_regles(run):
    settings, results = run
    out = nettoyer.output_path(settings)
    df = pd.read_parquet(out)
    assert results["nettoyer"].rows == len(df) > 0 and df["code"].is_unique
    assert (settings.clean_dir / f"rapport_nettoyage_{settings.stamp}.md").is_file()
    rules = json.loads((settings.clean_dir / f"regles_{settings.stamp}.json").read_text(encoding="utf-8"))
    assert [r["rule"] for r in rules["rules"]][:4] == ["type_columns", "normalize_texts", "filter_codes", "deduplicate_codes"]


def test_nettoyer_lots_identique_a_un_bloc(run, tmp_path):
    settings, _ = run
    single = make_settings(tmp_path, batches=1)
    single.raw_dir.mkdir(parents=True)
    shutil.copy(charger.output_path(settings), charger.output_path(single))
    assert run_step("nettoyer", nettoyer.run, single).status == "ok"
    a = pd.read_parquet(nettoyer.output_path(settings))
    b = pd.read_parquet(nettoyer.output_path(single))
    pd.testing.assert_frame_equal(a, b[a.columns], check_dtype=False)


def test_nettoyer_sans_entree_dit_quoi_lancer(tmp_path):
    result = run_step("nettoyer", nettoyer.run, make_settings(tmp_path))
    assert result.status == "failed" and "charger" in result.message and "Traceback" not in result.message


# ------------------------------------------------------------------ parquet

def test_parquet_complet_et_meme_comptage(run):
    settings, results = run
    final = parquet.output_dir(settings)
    assert (final / SUCCESS).is_file() and (final / "schema_products.json").is_file()
    assert results["parquet"].rows == results["nettoyer"].rows      # même source que la base
    assert any(p.name.startswith("pnns_group=") for p in (final / "produits").iterdir())


def test_parquet_relance_identique(run, tmp_path):
    settings, _ = run
    other = make_settings(tmp_path)
    other.clean_dir.mkdir(parents=True)
    shutil.copy(nettoyer.output_path(settings), nettoyer.output_path(other))
    assert run_step("parquet", parquet.run, other).status == "ok"
    first = tree_hashes(parquet.output_dir(settings))
    assert run_step("parquet", parquet.run, other).status == "ok"        # deux passages de suite
    assert tree_hashes(parquet.output_dir(other)) == first


def test_exports_sans_parquet_dit_quoi_lancer(tmp_path):
    result = run_step("exports", exports.run, make_settings(tmp_path))
    assert result.status == "failed" and "parquet" in result.message


def test_exports_ignore_un_dossier_sans_success(run, tmp_path):
    settings, _ = run
    other = make_settings(tmp_path)
    broken = parquet.output_dir(other)
    shutil.copytree(parquet.output_dir(settings), broken)
    (broken / SUCCESS).unlink()                                           # écriture « interrompue »
    result = run_step("exports", exports.run, other)
    assert result.status == "failed" and "_SUCCESS" in result.message


# ------------------------------------------------------------------ exports et split

def test_export_fige_et_reproductible(run):
    settings, _ = run
    path, _ = exports.output_paths(settings)
    before = sha256_file(path)
    assert run_step("exports", exports.run, settings).status == "skipped"           # refuse de réécrire
    assert run_step("exports", exports.run, settings, force=True).status == "ok"    # --force
    assert sha256_file(path) == before                                              # même empreinte


def test_split_stratifie_20_pourcent_par_grade(run):
    settings, _ = run
    df = export_frame(settings)
    assert set(df["split"]) == {"train", "test"}
    for grade, group in df.groupby("nutriscore_grade"):
        expected = round(0.2 * len(group))
        assert abs((group["split"] == "test").sum() - expected) <= 1, grade


def test_split_reproductible_produit_par_produit(run, tmp_path):
    settings, _ = run
    other = make_settings(tmp_path)
    shutil.copytree(parquet.output_dir(settings), parquet.output_dir(other))
    assert run_step("exports", exports.run, other).status == "ok"
    a = export_frame(settings).set_index("code")["split"]
    b = export_frame(other).set_index("code")["split"]
    assert a.equals(b)


def test_schema_decrit_le_fichier(run):
    settings, _ = run
    path, schema_path = exports.output_paths(settings)
    contract = json.loads(schema_path.read_text(encoding="utf-8"))
    df = pd.read_parquet(path)
    assert [c["name"] for c in contract["columns"]] == list(df.columns)
    assert contract["row_count"] == len(df) and contract["sha256"] == sha256_file(path)
    assert contract["split"]["seed"] == 42 and contract["split"]["test_fraction"] == 0.2
    assert contract["split"]["test_total"] == int((df["split"] == "test").sum())
    assert "ODbL" in contract["license"]


# ------------------------------------------------------------------ base, journal, CLI

def test_tables_de_la_base_sans_postgresql(run):
    pytest.importorskip("sqlalchemy")
    pytest.importorskip("sqlparse")
    pytest.importorskip("sqlalchemy_utils")          # importé par create_database au chargement du module
    from nutriscope import legacy  # noqa: F401
    from create_database import prepare_tables
    settings, results = run
    tables = prepare_tables(pd.read_parquet(nettoyer.output_path(settings)))
    assert len(tables["products"]) == results["nettoyer"].rows


def test_charger_base_sans_mot_de_passe_echoue_proprement(run):
    settings, _ = run
    result = run_step("charger_base", charger_base.run, settings)
    assert result.status == "failed" and "DB_PASSWORD" in result.message


@pytest.mark.skipif(os.environ.get("NUTRISCOPE_TEST_DB") != "1" or not os.environ.get("DB_PASSWORD"),
                    reason="PostgreSQL non configuré (NUTRISCOPE_TEST_DB=1 et DB_PASSWORD)")
def test_charger_base_postgresql_reel(run):
    settings, results = run
    from dataclasses import replace
    result = run_step("charger_base", charger_base.run, replace(settings, db_password=os.environ["DB_PASSWORD"]))
    assert result.status == "ok" and result.rows == results["nettoyer"].rows


def test_journal_trace_succes_et_echecs(run):
    settings, _ = run
    lines = journal.read(settings)
    steps = {line["step"] for line in lines if line["status"] == "ok"}
    assert {"charger", "nettoyer", "parquet", "exports"} <= steps
    assert all({"timestamp", "step", "status", "seconds", "rows"} <= set(line) for line in lines)
    assert any(line["status"] == "failed" for line in lines)          # l'échec sans mot de passe est journalisé


def test_cli_commande_unique_sans_base(tmp_path):
    env = {**os.environ, "NUTRISCOPE_DATA": str(tmp_path), "NUTRISCOPE_DATE": "20261014",
           "NUTRISCOPE_BATCHES": "2", "NUTRISCOPE_DUCKDB_MEMORY": "2GB", "PYTHONUTF8": "1"}
    env.pop("NUTRISCOPE_SOURCE", None)
    done = subprocess.run([sys.executable, "-m", "nutriscope.pipeline", "all", "--skip", "charger_base"],
                          cwd=tmp_path, env={**env, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (tmp_path / "exports" / "features_nutriscore_20261014.parquet").is_file()
