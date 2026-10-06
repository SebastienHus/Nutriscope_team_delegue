import duckdb
import shutil
import pandas as pd
import pyarrow.dataset as ds
import json
from pathlib import Path

def read_parquet(parquet: Path) -> pd.DataFrame:
    con = duckdb.connect()
    motif = (parquet / "**" / "*.parquet").as_posix()
    return con.execute(f"CREATE VIEW products AS SELECT * FROM read_parquet('{motif}', hive_partitioning = true)").df()

def to_parquet(source: Path, destination: Path, target: str="coalesce(pnns_groups_1, 'unknown')") -> Path:
    """Source -> Parquet partitionné par rayon"""
    if destination.is_dir():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    read = (
        f"read_parquet('{source.as_posix()}')"
        if source.suffix == ".parquet"
        else f"read_csv('{source.as_posix()}', types={{'code': 'VARCHAR'}}, sample_size=-1)"
    )

    duckdb.sql(f"""
        COPY (SELECT *, lower(regexp_replace({target}, '[^A-Za-z0-9]+', '-', 'g')) AS group
              FROM {read})
        TO '{destination.as_posix()}' (FORMAT PARQUET, PARTITION_BY (group), COMPRESSION ZSTD, OVERWRITE_OR_IGNORE)
    """)

    # Exporte le schéma. Fonctionne seulement sur des schémas simples de parquet
    dataset = ds.dataset(destination.as_posix(), format="parquet")
    with open((destination / "schema.json").as_posix(), "w") as file:
        json.dump(
            {field.name: str(field.type) for field in dataset.schema},
            file,
            indent=4
        )

    return destination

