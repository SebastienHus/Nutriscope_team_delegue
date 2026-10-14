"""
Étape 1 — `charger` : source (CSV ou Parquet) → brut figé `data/raw/produits_bruts_<AAAAMMJJ>.parquet` + manifeste.

Méthode validée par le banc d'essai du 14/10 (fichier complet : 4 535 553 lignes, 0 perdue, 23 s, 10,7 Go de pic) :
- DuckDB lit en flux (pas de `pd.concat` de tout le fichier en mémoire, cause de la saturation RAM) ;
- seules les colonnes retenues (`src/database_options.ini`, 41) sont gardées ; les absentes sont listées ;
- tout est lu en texte : le code-barres garde ses zéros de tête, aucun type n'est deviné
  (le typage reste la règle 1 du nettoyage du TP 9) ;
- export OFF tabulé : guillemets désactivés (quelques fiches contiennent un `"` isolé) ;
  CSV à virgules (échantillon) : guillemets standards ;
- tri par code (puis date de modification, nom) : deux exécutions écrivent le même fichier ;
- écriture dans un `.tmp` puis renommage : le fichier final n'existe que complet.

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

from nutriscope.duck import connect, count, ident, sql_str
from nutriscope.files import StepError, fingerprint, manifest, publish, rel, sha256_file, write_json
from nutriscope.steps.base import StepResult

PREFIX = "produits_bruts_"
SORT_COLUMNS = ("code", "last_modified_t", "product_name")
NO_QUOTE_FALLBACK = "\x01"            # si une version de DuckDB refuse quote = ''


def output_path(settings):
    return settings.raw_dir / f"{PREFIX}{settings.stamp}.parquet"


def wanted_columns() -> list[str]:
    from nutriscope import legacy  # noqa: F401  (ajoute src/ au chemin)
    from options import CONFIG
    return list(CONFIG["columns"])


def read_header(path, sep: str) -> list[str]:
    with open(path, "rb") as file:
        first = file.readline().decode("utf-8", errors="replace").rstrip("\r\n")
    return [name.strip().strip('"') for name in first.split(sep)]


def csv_relation(source, sep: str, quote: str) -> str:
    options = [
        sql_str(source), f"delim = {sql_str(sep)}", "header = true", "all_varchar = true",
        f"quote = {sql_str(quote)}", f"escape = {sql_str(quote)}",
        "max_line_size = 20000000", "ignore_errors = true",
    ]
    return "read_csv(" + ", ".join(options) + ")"


def run(settings, force: bool = False) -> StepResult:
    import duckdb

    source = settings.source
    if not source.is_file():
        raise StepError(f"Source introuvable : {source}. Indiquez-la avec --source ou la variable NUTRISCOPE_SOURCE.")
    out = output_path(settings)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.unlink(missing_ok=True)

    is_parquet = source.suffix.lower() == ".parquet"
    sep = settings.separator
    con = connect(settings)
    try:
        if is_parquet:
            header = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM read_parquet({sql_str(source)})").fetchall()]
        else:
            header = read_header(source, sep)
        wanted = wanted_columns()
        present = [c for c in wanted if c in header]
        missing = [c for c in wanted if c not in header]
        if "code" not in present:
            raise StepError(f"La source {source.name} n'a pas de colonne `code` (séparateur détecté : {sep!r} ; "
                            "forcez-le avec --sep ou NUTRISCOPE_SEP).")

        select = ",\n    ".join(f"CAST({ident(c)} AS VARCHAR) AS {ident(c)}" for c in present)
        order = ", ".join(f"{ident(c)} NULLS LAST" for c in SORT_COLUMNS if c in present)
        quote = "" if sep == "\t" else '"'

        def copy(quote_char: str) -> None:
            relation = f"read_parquet({sql_str(source)})" if is_parquet else csv_relation(source, sep, quote_char)
            con.execute(f"COPY (SELECT\n    {select}\nFROM {relation}\nORDER BY {order}) "
                        f"TO {sql_str(tmp)} (FORMAT PARQUET, COMPRESSION ZSTD)")

        try:
            copy(quote)
        except duckdb.Error as error:
            if quote == "" and any(word in str(error).lower() for word in ("quote", "escape")):
                tmp.unlink(missing_ok=True)
                quote = NO_QUOTE_FALLBACK
                copy(quote)
            else:
                raise
        rows = count(con, f"read_parquet({sql_str(tmp)})")
    finally:
        con.close()

    publish(tmp, out, settings.data_dir)
    manifest_path = out.with_name(out.stem + ".manifest.json")
    write_json(manifest_path, manifest("charger", settings, {
        "file": rel(out), "rows": rows, "sha256": sha256_file(out), "bytes": out.stat().st_size,
    }, {
        "source": {"file": rel(source), "fingerprint": fingerprint(source),
                   "separator": repr(sep), "quote": "désactivé" if quote != '"' else '"'},
        "columns_kept": present,
        "columns_missing_in_source": missing,
        "sort": list(c for c in SORT_COLUMNS if c in present),
        "duckdb_memory_limit": settings.duckdb_memory,
    }))
    message = f"{len(present)} colonnes" + (f", {len(missing)} absentes de la source" if missing else "")
    return StepResult("charger", rows=rows, outputs=[rel(out), rel(manifest_path)], message=message)
