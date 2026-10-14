"""
Étape 4 — `parquet` : nettoyé → `data/parquet/produits_<AAAAMMJJ>/` contenant
`produits/pnns_group=<rayon>/data_0.parquet`, `schema_products.json` et `_SUCCESS` (écrit en dernier).

Reprend les choix du TP 12 (`src/storage/convert_parquet.py` : types posés colonne par colonne,
partition par rayon, compression ZSTD) en important ses fonctions (`column_type`, `partition_expression`),
avec trois corrections exigées par le TP 13, faites ici sans modifier `src/` :
1. `ORDER BY code` + un seul thread : deux exécutions écrivent les mêmes octets (idempotence) ;
2. écriture dans `produits_<date>.tmp/`, `_SUCCESS` en dernier, puis renommage : jamais de dossier à moitié écrit ;
3. sortie datée, et suppression de l'ancienne version seulement à l'intérieur de `data/` (garde-fou).
Le comptage du Parquet est comparé à celui du nettoyé (même source que la base).

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

import json

from nutriscope.duck import connect, count, ident, sql_str
from nutriscope.files import SUCCESS, StepError, find_input, manifest, publish, rel, remove, write_json
from nutriscope.steps.base import StepResult
from nutriscope.steps.nettoyer import PREFIX as CLEAN_PREFIX

PREFIX = "produits_"
DATASET = "produits"
SCHEMA_FILENAME = "schema_products.json"


def output_dir(settings):
    return settings.parquet_dir / f"{PREFIX}{settings.stamp}"


def run(settings, force: bool = False) -> StepResult:
    from nutriscope import legacy  # noqa: F401
    from storage.convert_parquet import (COMPRESSION, GROUP_COLUMN, LICENSE, PARTITION_COLUMN,
                                         PARTITION_JUSTIFICATION, column_type, partition_expression)

    clean = find_input(settings.clean_dir, CLEAN_PREFIX, ".parquet", settings.stamp, producer="nettoyer",
                       what="nettoyé (produits_propres_<date>.parquet)")
    final = output_dir(settings)
    tmp = final.with_name(final.name + ".tmp")
    remove(tmp, settings.data_dir)                       # reste d'une exécution interrompue
    dataset = tmp / DATASET
    tmp.mkdir(parents=True)                              # COPY ne crée pas les dossiers parents

    con = connect(settings, threads=1)                   # un seul thread : fichiers identiques d'une exécution à l'autre
    try:
        source = f"read_parquet({sql_str(clean)})"
        columns = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()]
        if GROUP_COLUMN not in columns:
            raise StepError(f"Colonne {GROUP_COLUMN} absente du nettoyé : impossible de partitionner par rayon.")
        casts = ",\n    ".join(f"CAST({ident(c)} AS {column_type(c)[0]}) AS {ident(c)}" for c in columns)
        con.execute(f"""
            COPY (
                SELECT
                    {casts},
                    {partition_expression()} AS {PARTITION_COLUMN}
                FROM {source}
                ORDER BY "code"
            )
            TO {sql_str(dataset)}
            (FORMAT PARQUET, PARTITION_BY ({PARTITION_COLUMN}), COMPRESSION {COMPRESSION.upper()})
        """)
        pattern = (dataset.resolve() / "**" / "*.parquet").as_posix()
        view = (f"read_parquet({sql_str(pattern)}, hive_partitioning = true, "
                f"hive_types = {{'{PARTITION_COLUMN}': VARCHAR}})")
        rows = count(con, view)
        clean_rows = count(con, source)
        partitions = con.execute(f"SELECT {PARTITION_COLUMN}, count(*) FROM {view} GROUP BY 1 ORDER BY 1").fetchall()
        described = con.execute(f"DESCRIBE SELECT * FROM {view}").fetchall()
    finally:
        con.close()

    if rows != clean_rows:
        raise StepError(f"Comptage différent : {rows} lignes dans le Parquet pour {clean_rows} dans le nettoyé.")

    schema = {
        "dataset": f"{rel(final)}/{DATASET}",
        "source": rel(clean),
        "format": "parquet",
        "partition_key": {"name": PARTITION_COLUMN, "source_column": GROUP_COLUMN, "expression": partition_expression()},
        "compression": COMPRESSION,
        "sorted_by": "code",
        "row_count": rows,
        "partitions": {group: n for group, n in partitions},
        "columns": [{"name": name, "type": sql_type,
                     "justification": PARTITION_JUSTIFICATION if name == PARTITION_COLUMN else column_type(name)[1]}
                    for name, sql_type, *_ in described],
        "license": LICENSE,
    }
    (tmp / SCHEMA_FILENAME).write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (tmp / SUCCESS).write_text("", encoding="utf-8")     # en dernier : le dossier est complet
    publish(tmp, final, settings.data_dir)

    manifest_path = write_json(final.with_name(final.name + ".manifest.json"), manifest("parquet", settings, {
        "directory": rel(final), "rows": rows, "partitions": len(partitions),
    }, {"input": {"file": rel(clean), "rows": clean_rows}, "controls": {"rows_equal_clean": True}}))
    return StepResult("parquet", rows=rows, outputs=[rel(final), rel(manifest_path)],
                      message=f"{len(partitions)} partitions (rayons)")
