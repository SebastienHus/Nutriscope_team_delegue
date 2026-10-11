"""
Tests pytest du stockage analytique — TP 12.

Conversion en Parquet partitionné (`storage.convert_parquet`) et export d'entraînement
figé (`storage.export_features`). Les tests tournent sur l'échantillon partagé, nettoyé
une fois par session, jamais sur l'extrait complet.
"""

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import pytest

import schema
from cleaning import clean
from options import CONFIG
from reader import read_products
from storage.convert_parquet import (
    PARTITION_COLUMN,
    SCHEMA_FILENAME,
    VIEW_NAME,
    open_products,
    to_parquet,
)
from storage.export_features import (
    FEATURES,
    TARGET,
    TARGET_GRADES,
    export_features,
    export_paths,
    sha256,
)

ROOT = Path(__file__).parent.parent
SAMPLE_PATH = ROOT / "data-nutriscope" / "echantillon_france.csv"
EXPORT_SCRIPT = ROOT / "src" / "storage" / "export_features.py"
FREEZE_DATE = date(2026, 10, 8)


def slug(group: str) -> str:
    """Slug attendu d'un rayon (même règle que `convert_parquet.partition_expression`)."""
    group = group.strip() if isinstance(group, str) and group.strip() else schema.UNKNOWN_GROUP
    return re.sub(r"[^a-z0-9]+", "-", group.lower()).strip("-")


def query(root: Path, sql: str) -> list[tuple]:
    """Exécute `sql` sur la vue `products` du jeu partitionné `root`."""
    con = duckdb.connect()
    try:
        open_products(con, root)
        return con.execute(sql).fetchall()
    finally:
        con.close()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def clean_csv(tmp_path_factory) -> Path:
    """Échantillon nettoyé par `cleaning.clean()`, écrit comme le fait `pipeline.py`."""
    if not SAMPLE_PATH.exists():
        pytest.skip(f"Échantillon absent : {SAMPLE_PATH}")
    df_clean, _ = clean(read_products(SAMPLE_PATH, CONFIG["columns"]))
    path = tmp_path_factory.mktemp("clean") / "products.csv"
    df_clean.to_csv(path, index=False)
    return path


@pytest.fixture(scope="session")
def clean_df(clean_csv) -> pd.DataFrame:
    return pd.read_csv(clean_csv, dtype={"code": str})


@pytest.fixture(scope="session")
def parquet_root(clean_csv, tmp_path_factory) -> Path:
    destination = tmp_path_factory.mktemp("parquet") / "products"
    to_parquet(clean_csv, destination)
    return destination


@pytest.fixture(scope="session")
def export(parquet_root, tmp_path_factory) -> tuple[Path, Path]:
    output_dir = tmp_path_factory.mktemp("exports")
    return export_features(parquet_root, output_dir, freeze_date=FREEZE_DATE)


@pytest.fixture
def tiny_csv(tmp_path) -> Path:
    """Catalogue nettoyé minimal : un code à zéros de tête, un rayon vide."""
    path = tmp_path / "tiny.csv"
    pd.DataFrame({
        "code": ["0012345678905", "3017620422003"],
        "pnns_groups_1": ["Sugary snacks", ""],
        "nutriscore_grade": ["d", "a"],
        "energy-kcal_100g": [322.0, 50.0],
        "nova_group": pd.array([4, None], dtype="Int64"),   # écrit « 4 » et « », comme le nettoyage
        "created_t": ["2019-08-14 02:43:10", "2020-01-01 00:00:00"],
        "fat_100g_missing": [False, True],
    }).to_csv(path, index=False)
    return path


# ============================================================================
# CONVERSION
# ============================================================================

def test_one_partition_per_pnns_group(parquet_root, clean_df):
    folders = {path.name for path in parquet_root.iterdir() if path.is_dir()}
    expected = {f"{PARTITION_COLUMN}={slug(group)}" for group in clean_df["pnns_groups_1"].unique()}
    assert folders == expected


def test_conversion_keeps_all_rows(parquet_root, clean_df):
    assert query(parquet_root, f"SELECT count(*) FROM {VIEW_NAME}")[0][0] == len(clean_df)


def test_types_are_posed(parquet_root):
    types = dict(row[:2] for row in query(parquet_root, f"DESCRIBE {VIEW_NAME}"))
    assert types["code"] == "VARCHAR"
    assert types["energy-kcal_100g"] == "FLOAT"
    assert types["additives_n"] == "SMALLINT"
    assert types["nutriscore_score"] == "SMALLINT"
    assert types["nova_group"] == "TINYINT"
    assert types["created_t"] == "TIMESTAMP"
    assert types["last_modified_t"] == "TIMESTAMP"
    assert types[PARTITION_COLUMN] == "VARCHAR"


def test_schema_products_matches_dataset(parquet_root, clean_df):
    written = json.loads((parquet_root.parent / SCHEMA_FILENAME).read_text(encoding="utf-8"))
    types = [list(row[:2]) for row in query(parquet_root, f"DESCRIBE {VIEW_NAME}")]
    assert [[column["name"], column["type"]] for column in written["columns"]] == types
    assert all(column["justification"] for column in written["columns"])
    assert written["partition_key"]["name"] == PARTITION_COLUMN
    assert written["compression"] == "zstd"
    assert written["row_count"] == len(clean_df) == sum(written["partitions"].values())
    assert "ODbL" in written["license"]


def test_leading_zeros_survive_and_blank_group_is_unknown(tiny_csv, tmp_path):
    destination = tmp_path / "products"
    to_parquet(tiny_csv, destination)
    rows = dict(query(destination, f"SELECT code, {PARTITION_COLUMN} FROM {VIEW_NAME}"))
    assert rows == {"0012345678905": "sugary-snacks", "3017620422003": schema.UNKNOWN_GROUP}


def test_conversion_is_replayable(tiny_csv, tmp_path):
    destination = tmp_path / "products"
    to_parquet(tiny_csv, destination)
    orphan = destination / f"{PARTITION_COLUMN}=orphan" / "data_0.parquet"
    orphan.parent.mkdir()
    orphan.write_bytes(b"")
    to_parquet(tiny_csv, destination)
    assert not orphan.parent.exists()
    assert query(destination, f"SELECT count(*) FROM {VIEW_NAME}")[0][0] == 2


# ============================================================================
# EXPORT D'ENTRAÎNEMENT
# ============================================================================

def test_export_is_dated_and_described(export):
    parquet_path, schema_path = export
    assert parquet_path.name == "features_nutriscore_20261008.parquet"
    assert schema_path.name == "features_nutriscore_20261008.schema.json"
    contract = json.loads(schema_path.read_text(encoding="utf-8"))
    assert contract["freeze_date"] == FREEZE_DATE.isoformat()
    assert contract["sha256"] == sha256(parquet_path)
    assert contract["target"] == TARGET
    assert sum(grade["count"] for grade in contract["target_distribution"].values()) == contract["row_count"]
    assert "ODbL" in contract["license"]


def test_export_schema_lists_parquet_columns_in_order(export):
    parquet_path, schema_path = export
    contract = json.loads(schema_path.read_text(encoding="utf-8"))
    columns = list(pd.read_parquet(parquet_path).columns)
    assert [column["name"] for column in contract["columns"]] == columns
    assert columns == [feature.name for feature in FEATURES]


def test_export_target_has_no_missing(export):
    df = pd.read_parquet(export[0])
    assert len(df) > 0
    assert df[TARGET].notna().all()
    assert set(df[TARGET]) <= set(TARGET_GRADES)
    assert df["code"].is_unique


def test_export_keeps_only_usable_products(export):
    df = pd.read_parquet(export[0])
    assert df[schema.KEY_NUTRIENTS].notna().all().all()
    assert (df["energy-kcal_100g"] > 0).all()
    assert schema.sugars_within_carbohydrates(df).all()
    assert schema.saturated_within_fat(df).all()


def test_export_refuses_to_overwrite(export, parquet_root):
    with pytest.raises(FileExistsError):
        export_features(parquet_root, export[0].parent, freeze_date=FREEZE_DATE)


def test_export_force_is_reproducible(export, parquet_root):
    parquet_path, _ = export
    before = sha256(parquet_path)
    export_features(parquet_root, parquet_path.parent, force=True, freeze_date=FREEZE_DATE)
    assert sha256(parquet_path) == before


def test_cli_refuses_to_overwrite(parquet_root, tmp_path):
    command = [sys.executable, str(EXPORT_SCRIPT), "-i", str(parquet_root), "-o", str(tmp_path)]
    assert subprocess.run(command, capture_output=True).returncode == 0
    assert subprocess.run(command, capture_output=True).returncode == 1
    assert export_paths(tmp_path, date.today())[0].exists()
