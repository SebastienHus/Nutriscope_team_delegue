"""Petits outils DuckDB communs aux étapes."""

from __future__ import annotations

from pathlib import Path


def sql_str(value) -> str:
    """Littéral SQL ; un chemin est rendu absolu au format POSIX (C:/Users/... fonctionne sous Windows)."""
    if isinstance(value, Path):
        value = value.resolve().as_posix()
    return "'" + str(value).replace("'", "''") + "'"


def ident(name: str) -> str:
    """Identifiant entre guillemets : des colonnes contiennent un tiret (`energy-kcal_100g`)."""
    return '"' + name.replace('"', '""') + '"'


def connect(settings, threads: int | None = None):
    """Connexion DuckDB avec plafond mémoire et débordement sur disque dans `data/tmp/`."""
    import duckdb

    con = duckdb.connect()
    con.execute(f"SET memory_limit = {sql_str(settings.duckdb_memory)}")
    settings.tmp_dir.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory = {sql_str(settings.tmp_dir / 'duckdb')}")
    threads = threads or settings.duckdb_threads
    if threads:
        con.execute(f"SET threads = {int(threads)}")
    return con


def count(con, relation: str) -> int:
    return int(con.execute(f"SELECT count(*) FROM {relation}").fetchone()[0])
