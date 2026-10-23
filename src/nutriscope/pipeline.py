"""
Pipeline bout-en-bout NutriScope — TP 13 (jalon J3).

Une commande unique va du CSV Open Food Facts brut aux données prêtes pour le ML, en cinq
étapes lançables séparément. Chaque étape résout elle-même son entrée (la sortie datée du
jour, sinon la plus récente), écrit des sorties datées `<AAAAMMJJ>` et consigne une ligne
dans le journal des durées `data/logs/pipeline_runs.jsonl`, y compris en cas d'échec.

Les sorties de chaque source vivent dans leur propre dossier, `data/<source>/`, nommé
d'après le fichier source (`echantillon_france`, `en-openfoodfacts-org-products`) ou
forcé avec `--name`. L'échantillon et l'extrait complet ne s'écrasent donc jamais, et
chacun a son propre export figé. Le journal des durées reste commun à toutes les sources.

| Étape           | Entrée               | Sortie (dans `data/<source>/`)                               |
| --------------- | -------------------- | ------------------------------------------------------------ |
| `load`          | CSV ou Parquet brut  | `raw/products_raw_<date>.parquet` + `.manifest.json`         |
| `clean_data`    | brut                 | `clean/products_clean_<date>.parquet` + rapport + règles     |
| `load_database` | nettoyé              | base PostgreSQL rechargée + `db/load_database_<date>.json`   |
| `parquet`       | nettoyé              | `parquet/products_<date>/` (par rayon, `_SUCCESS`) + schéma  |
| `exports`       | Parquet              | `exports/features_nutriscore_<date>.parquet` + `.schema.json` |

Gros volumes (extrait complet, 13 Go, environ 4,5 millions de lignes) : `load` lit la source
avec DuckDB, en flux et sans rien charger dans pandas ; `clean_data` nettoie par lots de
produits (répartis par code-barres), sans jamais garder le brut complet en mémoire. Méthode
reprise de la proposition alternative du TP 13 (branche `tp13-alternative-proposition`),
voir `docs/data/pipeline.md`.

`load_database` et `parquet` partent du même nettoyé (source de vérité unique) et
vérifient tous deux que leur nombre de produits est celui du nettoyé. Sans PostgreSQL
configuré, `load_database` est ignorée avec un avertissement (`--require-db` la rend
obligatoire). Les noms de l'énoncé (`charger`, `nettoyer`, `charger_base`) sont acceptés.

    python -m nutriscope.pipeline all                       # échantillon partagé
    python -m nutriscope.pipeline exports                   # une étape seule
    python -m nutriscope.pipeline all --full                # extrait complet (data/), 8 lots
    python -m nutriscope.pipeline clean_data --batches 4 --memory 8GB
    python -m nutriscope.pipeline exports --date 20261014 --force
    python -m nutriscope.pipeline purge [--full | --name N] [--include-exports]   # une source
    python -m nutriscope.pipeline purge -a [--include-exports]                    # toutes

Données : © Open Food Facts contributors — ODbL.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .cleaning import DEFAULT_STRATEGY, clean
from .options import CONFIG, DATA_PATH, ROOT_PATH, SHARED_DATA_PATH
from .report import merge_reports, merge_summaries, render_report, summarize_before
from .storage.convert_parquet import (LICENSE, is_complete, relative_path, sql_identifier, sql_string,
                                      to_parquet)
from .storage.export_features import export_features, git_commit, sha256

# ============================================================================
# CONSTANTES
# ============================================================================

SOURCE_ENV = "NUTRISCOPE_SOURCE"
DEFAULT_SOURCE = SHARED_DATA_PATH / "echantillon_france.csv"
FULL_SOURCE = DATA_PATH / "en.openfoodfacts.org.products.csv"
DATE_FORMAT = "%Y%m%d"

STEPS = ("load", "clean_data", "load_database", "parquet", "exports")
ALIASES = {"charger": "load", "nettoyer": "clean_data", "charger_base": "load_database"}
COMMANDS = (*STEPS, "all", "purge")

OK, SKIPPED, FAILED = "ok", "skipped", "failed"
JOURNAL = Path("logs") / "pipeline_runs.jsonl"
TMP = Path("tmp")                       # débordement DuckDB et lots du nettoyage, vidé par purge
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
# Noms interdits pour un dossier de source : le journal, et les dossiers de l'ancienne
# organisation (sorties directement dans data/, avant le 23/10), que purge -a nettoie aussi
RESERVED_NAMES = {"logs", "tmp", "raw", "clean", "db", "parquet", "exports", "docs"}

# Gros volumes : mesures de la proposition alternative du TP 13 (fichier complet, 4 535 553 lignes)
AUTO_BATCH_ROWS = 1_000_000             # au-delà, nettoyage par lots ; en dessous, un seul bloc
DEFAULT_BATCHES = 8                     # 8 lots : 2,5 Go de pic au lieu de 14,1 Go en un bloc
FAST_FINGERPRINT_BYTES = 1 << 30        # au-delà de 1 Go, empreinte rapide de la source
CSV_MAX_LINE_SIZE = 20_000_000          # quelques fiches ont des listes d'ingrédients très longues
NO_QUOTE_FALLBACK = "\x01"              # si DuckDB refuse quote = '' (guillemets désactivés)
VERSIONED_PACKAGES = ("duckdb", "pandas", "pyarrow", "numpy", "pandera")

# Connexion PostgreSQL : variables d'environnement, ou fichier de mot de passe (secrets/)
DB_ENV = {
    "username": ("NUTRISCOPE_DB_USER", "postgres"),
    "host": ("NUTRISCOPE_DB_HOST", "localhost"),
    "port": ("NUTRISCOPE_DB_PORT", "5432"),
}
DB_PASSWORD_ENV = "NUTRISCOPE_DB_PASSWORD"
DB_PASSWORD_FILE_ENV = "NUTRISCOPE_DB_PASSWORD_FILE"
DEFAULT_DB_PASSWORD_FILE = ROOT_PATH / "secrets" / "db_password.txt"


@dataclass(frozen=True)
class Artifact:
    """Sortie datée d'une étape : `<data>/<folder>/<prefix><AAAAMMJJ><suffix>`."""
    folder: str
    prefix: str
    suffix: str
    producer: str           # étape à lancer si l'artefact manque
    description: str

    def pattern(self) -> re.Pattern:
        return re.compile(rf"^{re.escape(self.prefix)}(\d{{8}}){re.escape(self.suffix)}$")


RAW = Artifact("raw", "products_raw_", ".parquet", "load", "raw dataset")
CLEAN = Artifact("clean", "products_clean_", ".parquet", "clean_data", "cleaned dataset")
PARQUET = Artifact("parquet", "products_", "", "parquet", "partitioned Parquet dataset")
EXPORT = Artifact("exports", "features_nutriscore_", ".parquet", "exports", "features export")

# Fichiers que `purge` a le droit de supprimer (jamais les sources ni les anciens fichiers non datés)
PURGEABLE = (
    ("raw", re.compile(r"^products_raw_\d{8}\.(parquet|manifest\.json)$")),
    ("clean", re.compile(r"^(products_clean_\d{8}\.parquet|cleaning_report_\d{8}\.md|cleaning_rules_\d{8}\.json)$")),
    ("db", re.compile(r"^load_database_\d{8}\.json$")),
    ("parquet", re.compile(r"^products_\d{8}(\.schema\.json)?$")),
)
PURGEABLE_EXPORTS = ("exports", re.compile(r"^features_nutriscore_\d{8}\.(parquet|schema\.json)$"))


class MissingInputError(FileNotFoundError):
    """L'entrée d'une étape est introuvable : le message dit quelle étape lancer avant."""


@dataclass
class StepOutcome:
    """Ce qu'une étape a produit."""
    rows: int | None = None
    outputs: list[Path] = field(default_factory=list)
    status: str = OK
    message: str = ""


@dataclass
class StepResult:
    """Ligne du journal des durées."""
    timestamp: str
    run_id: str             # commun aux étapes d'une même commande : regroupe une exécution
    run_date: str
    source: str             # source brute traitée, relative au dépôt
    name: str               # dossier de sorties de la source : data/<name>/
    step: str
    status: str
    duration_s: float
    rows: int | None
    outputs: list[str]
    message: str
    options: dict           # options qui changent le calcul ou la mémoire (lots, plafond DuckDB, force)


# ============================================================================
# OUTILS
# ============================================================================

def detect_separator(path: Path) -> str:
    """Séparateur d'un export CSV, déduit de sa ligne d'en-tête (tabulation ou virgule)."""
    with open(path, encoding="utf-8", errors="replace") as file:
        header = file.readline()
    return "\t" if header.count("\t") > header.count(",") else ","


def read_header(path: Path, sep: str) -> list[str]:
    """Noms de colonnes d'un CSV, lus sur la première ligne."""
    with open(path, "rb") as file:
        first = file.readline().decode("utf-8", errors="replace").rstrip("\r\n")
    return [name.strip().strip('"') for name in first.split(sep)]


def csv_relation(path: Path, sep: str, quote: str) -> str:
    """
    Relation DuckDB qui lit un CSV en flux, tout en texte (`all_varchar`) : le code-barres
    garde ses zéros de tête et aucun type n'est deviné (le typage est la règle 1 du
    nettoyage). Pour l'export tabulé d'Open Food Facts, les guillemets sont désactivés :
    quelques fiches contiennent un `"` isolé qui ferait fusionner des lignes.
    """
    options = [
        sql_string(path), f"delim = {sql_string(sep)}", "header = true", "all_varchar = true",
        f"quote = {sql_string(quote)}", f"escape = {sql_string(quote)}",
        f"max_line_size = {CSV_MAX_LINE_SIZE}", "ignore_errors = true",
    ]
    return "read_csv(" + ", ".join(options) + ")"


def fingerprint(path: Path) -> dict:
    """
    Empreinte de la source : SHA-256 complet jusqu'à 1 Go ; au-delà (export complet de
    13 Go, plusieurs minutes de lecture), taille, date de modification et SHA-256 du premier Mo.
    """
    size = path.stat().st_size
    if size <= FAST_FINGERPRINT_BYTES:
        return {"method": "sha256", "value": sha256(path), "bytes": size}
    with open(path, "rb") as file:
        head = hashlib.sha256(file.read(1 << 20)).hexdigest()
    return {"method": "fast (bytes + mtime + sha256 of the first MiB)", "value": head, "bytes": size,
            "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}


def library_versions() -> dict:
    """Versions des bibliothèques qui écrivent les fichiers : l'empreinte d'un Parquet en dépend."""
    from importlib import metadata

    versions = {}
    for name in VERSIONED_PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Écrit `df` en Parquet sans jamais laisser de fichier à moitié écrit (écriture puis renommage)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    df.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=_json_default) + "\n",
                    encoding="utf-8")


def _json_default(value):
    """Convertit les scalaires NumPy des comptes rendus en types JSON."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Path):
        return relative_path(value)
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def relative_message(message: str) -> str:
    """
    Retire le chemin absolu du dépôt d'un message (exception d'une bibliothèque, par
    exemple) : le journal ne doit contenir aucun chemin propre à un poste.
    """
    root = ROOT_PATH.resolve()
    for prefix in {str(root), root.as_posix()}:
        for separator in ("\\", "/"):
            message = message.replace(prefix + separator, "")
    return message


def count_rows(path: Path) -> int:
    """Nombre de lignes d'un fichier Parquet."""
    return duckdb.sql(f"SELECT count(*) FROM read_parquet({sql_string(path)})").fetchone()[0]


def source_name(path: Path) -> str:
    """
    Nom du dossier de sorties d'une source : nom du fichier sans extension, en minuscules,
    chaque suite de caractères hors `a-z`, `0-9` et `_` remplacée par un tiret.
    `en.openfoodfacts.org.products.csv` → `en-openfoodfacts-org-products`.
    """
    return re.sub(r"[^a-z0-9_]+", "-", Path(path).stem.lower()).strip("-") or "source"


def check_name(name: str) -> str:
    """Refuse un nom de dossier de source invalide ou réservé (journal, ancienne organisation)."""
    if not NAME_PATTERN.match(name) or name in RESERVED_NAMES:
        raise ValueError(f"Invalid output name {name!r}: lowercase letters, digits, '_' or '-', "
                         f"and not one of {sorted(RESERVED_NAMES)}")
    return name


def _purge_folder(root: Path, include_exports: bool) -> list[Path]:
    """Sorties datées et dossier temporaire d'un dossier de source."""
    targets = [*PURGEABLE, PURGEABLE_EXPORTS] if include_exports else list(PURGEABLE)
    removed = []
    temporary = root / TMP
    if temporary.is_dir():
        shutil.rmtree(temporary)
        removed.append(temporary)
    for folder, pattern in targets:
        directory = root / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if not pattern.match(path.name):
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(path)
    return removed


def purge(data_dir: Path = DATA_PATH, name: str | None = None, include_exports: bool = False) -> list[Path]:
    """
    Supprime les sorties datées du pipeline et retourne les chemins supprimés.

    Avec `name`, seulement celles de la source `data/<name>/` ; sans `name` (`purge -a`),
    celles de toutes les sources, ainsi que les sorties datées de l'ancienne organisation
    (directement dans `data/`). Vide aussi les dossiers `tmp/`. Ne touche ni aux sources
    (`data/*.csv`), ni aux fichiers non datés, ni au journal des durées. Les exports figés
    ne sont supprimés qu'avec `include_exports`.
    """
    data_dir = Path(data_dir)
    if name is not None:
        roots = [data_dir / check_name(name)]
    else:
        roots = [data_dir, *sorted(path for path in data_dir.iterdir()
                                   if path.is_dir() and path.name not in RESERVED_NAMES)] \
            if data_dir.is_dir() else []
    removed = []
    for root in roots:
        removed.extend(_purge_folder(root, include_exports))
    return removed


# ============================================================================
# PIPELINE
# ============================================================================

class Pipeline:
    """
    Les cinq étapes du pipeline. Chaque étape a la même signature : elle ne prend que
    l'état du pipeline, résout son entrée, et retourne un `StepOutcome` (lignes, sorties).
    `run()` la chronomètre et l'inscrit au journal ; `run_all()` les enchaîne.
    """

    def __init__(self, source: Path | None = None, sep: str | None = None,
                 data_dir: Path = DATA_PATH, run_date: date | None = None, force: bool = False,
                 require_db: bool = False, batches: int | None = None, memory: str | None = None,
                 name: str | None = None,
                 db_password_file: Path = DEFAULT_DB_PASSWORD_FILE, verbose: bool = True):
        self.source = Path(source or os.environ.get(SOURCE_ENV) or DEFAULT_SOURCE)
        self.sep = sep
        self.data_dir = Path(data_dir)                  # racine : journal commun, un dossier par source
        self.name = check_name(name or source_name(self.source))
        self.output_dir = self.data_dir / self.name     # sorties de cette source
        self.run_date = run_date or date.today()
        self.force = force
        self.require_db = require_db
        self.batches = batches          # None : automatique (un bloc, ou 8 lots au-delà d'1 M de lignes)
        self.memory = memory            # plafond mémoire DuckDB, ex. "12GB" (None : défaut de DuckDB)
        self.db_password_file = Path(db_password_file)
        self.verbose = verbose
        self.run_id = datetime.now().strftime("%Y%m%dT%H%M%S")

    # ------------------------------------------------------------------ chemins

    @property
    def tag(self) -> str:
        return self.run_date.strftime(DATE_FORMAT)

    def dated(self, artifact: Artifact) -> Path:
        """Chemin de l'artefact pour la date d'exécution."""
        return self.output_dir / artifact.folder / f"{artifact.prefix}{self.tag}{artifact.suffix}"

    def resolve(self, artifact: Artifact) -> Path:
        """
        Entrée d'une étape : l'artefact daté du jour d'exécution, sinon le plus récent
        antérieur. Lève `MissingInputError` en nommant l'étape à lancer avant. Un dossier
        Parquet sans `_SUCCESS` est une écriture interrompue : il est refusé.
        """
        directory = self.output_dir / artifact.folder
        pattern = artifact.pattern()
        candidates = sorted(
            (match.group(1), path)
            for path in (directory.iterdir() if directory.is_dir() else [])
            if (match := pattern.match(path.name)) and match.group(1) <= self.tag
        )
        if not candidates:
            raise MissingInputError(
                f"No {artifact.description} dated {self.tag} or earlier in {relative_path(directory)}: "
                f"run the `{artifact.producer}` step first."
            )
        path = candidates[-1][1]
        if artifact is PARQUET and not is_complete(path):
            raise MissingInputError(
                f"{relative_path(path)} is incomplete (no _SUCCESS marker, interrupted run): "
                f"run the `{artifact.producer}` step again."
            )
        return path

    def connect(self, threads: int | None = None) -> duckdb.DuckDBPyConnection:
        """Connexion DuckDB : plafond mémoire éventuel, débordement sur disque dans `data/<source>/tmp/`."""
        con = duckdb.connect()
        if self.memory:
            con.execute(f"SET memory_limit = {sql_string(self.memory)}")
        spill = self.output_dir / TMP / "duckdb"
        spill.mkdir(parents=True, exist_ok=True)
        con.execute(f"SET temp_directory = {sql_string(spill)}")
        if threads:
            con.execute(f"SET threads = {int(threads)}")
        return con

    # ------------------------------------------------------------------ étapes

    def load(self) -> StepOutcome:
        """
        Source brute → `raw/products_raw_<date>.parquet` + manifeste (empreinte de la source).

        DuckDB lit la source en flux et écrit directement le Parquet : rien ne passe par
        pandas, la mémoire reste bornée même sur l'export complet. Seules les colonnes de
        `options.ini` sont gardées (les absentes sont listées dans le manifeste),
        toutes en texte. Les lignes sont triées sur toutes les colonnes (code en premier) :
        deux exécutions écrivent le même fichier.
        """
        if not self.source.is_file():
            raise MissingInputError(
                f"Source not found: {relative_path(self.source)}. Put the Open Food Facts export there, "
                f"pass --source, or set {SOURCE_ENV}."
            )
        is_parquet = self.source.suffix == ".parquet"
        sep = None if is_parquet else (self.sep or detect_separator(self.source))
        output = self.dated(RAW)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        temporary.unlink(missing_ok=True)

        con = self.connect()
        try:
            if is_parquet:
                header = [row[0] for row in con.execute(
                    f"DESCRIBE SELECT * FROM read_parquet({sql_string(self.source)})").fetchall()]
            else:
                header = read_header(self.source, sep)
            present = [column for column in CONFIG["columns"] if column in header]
            missing = [column for column in CONFIG["columns"] if column not in header]
            if "code" not in present:
                raise ValueError(f"No `code` column in {self.source.name} (separator {sep!r}): "
                                 "force the separator with --sep")

            select = ", ".join(f"CAST({sql_identifier(c)} AS VARCHAR) AS {sql_identifier(c)}" for c in present)
            quote = "" if sep == "\t" else '"'

            def copy(quote_char: str) -> None:
                relation = (f"read_parquet({sql_string(self.source)})" if is_parquet
                            else csv_relation(self.source, sep, quote_char))
                con.execute(f"COPY (SELECT {select} FROM {relation} ORDER BY ALL) "
                            f"TO {sql_string(temporary)} (FORMAT PARQUET, COMPRESSION ZSTD)")

            try:
                copy(quote)
            except duckdb.Error as error:
                if quote != "" or not any(word in str(error).lower() for word in ("quote", "escape")):
                    raise
                temporary.unlink(missing_ok=True)
                quote = NO_QUOTE_FALLBACK
                copy(quote)
            rows = con.execute(f"SELECT count(*) FROM read_parquet({sql_string(temporary)})").fetchone()[0]
        finally:
            con.close()
        os.replace(temporary, output)

        manifest = output.with_suffix(".manifest.json")
        write_json({
            "step": "load",
            "source": relative_path(self.source),
            "source_fingerprint": fingerprint(self.source),
            "separator": sep,
            "quote": None if is_parquet else ("disabled" if quote != '"' else '"'),
            "rows": rows,
            "columns": present,
            "columns_missing_in_source": missing,
            "output": relative_path(output),
            "output_sha256": sha256(output),
            "created_at": datetime.now().isoformat(timespec="seconds"),   # horodatage : ici, pas dans les données
            "git_commit": git_commit(),
            "versions": library_versions(),
            "license": LICENSE,
        }, manifest)
        message = f"{len(present)} columns" + (f", {len(missing)} missing in source" if missing else "")
        return StepOutcome(rows=rows, outputs=[output, manifest], message=message)

    def clean_data(self) -> StepOutcome:
        """
        Brut → nettoyé (règles du TP 9, dans l'ordre) + rapport Markdown + journal des règles.

        Au-delà d'un million de lignes brutes (ou avec `batches`), le brut est nettoyé par
        lots : le lot i reçoit les produits dont le code-barres, espaces retirés comme le fait
        `filter_codes`, vérifie `hash(code) % N = i`. Toutes les fiches d'un même code sont
        donc dans le même lot et la déduplication reste exacte ; les comptes rendus et le
        résumé du brut s'additionnent d'un lot à l'autre. Le résultat est le même qu'en un
        seul bloc, avec une mémoire bornée par la taille d'un lot.
        """
        raw_path = self.resolve(RAW)
        raw_rows = count_rows(raw_path)
        batches = self.batches or (DEFAULT_BATCHES if raw_rows > AUTO_BATCH_ROWS else 1)
        if batches < 1:
            raise ValueError(f"batches must be at least 1, got {batches}")

        parts, batch_reports, summaries, per_batch = [], [], [], []
        for index, batch in enumerate(self._raw_batches(raw_path, batches)):
            summaries.append(summarize_before(batch))
            cleaned, reports = clean(batch, DEFAULT_STRATEGY)
            per_batch.append({"batch": index, "rows_in": len(batch), "rows_out": len(cleaned)})
            parts.append(cleaned)
            batch_reports.append(reports)
            del batch

        cleaned = pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
        del parts
        if cleaned["code"].duplicated().any():
            raise RuntimeError("Duplicate barcodes after batched cleaning: the batch split is wrong")
        cleaned = cleaned.sort_values("code", kind="stable").reset_index(drop=True)
        reports = merge_reports(batch_reports)

        output = self.dated(CLEAN)
        write_parquet(cleaned, output)

        report_path = output.with_name(f"cleaning_report_{self.tag}.md")
        report_path.write_text(
            render_report(merge_summaries(summaries), cleaned, reports, source=raw_path.name,
                          date=f"données du {self.run_date.isoformat()}"),
            encoding="utf-8")
        rules_path = output.with_name(f"cleaning_rules_{self.tag}.json")
        write_json({
            "input": raw_path,
            "output": output,
            "rows_before": raw_rows,
            "rows_after": len(cleaned),
            "batches": batches,
            "batch_rule": "hash(code without spaces) % N" if batches > 1 else "single block",
            "per_batch": per_batch,
            "rules": [asdict(report) for report in reports],
            "license": LICENSE,
        }, rules_path)
        return StepOutcome(rows=len(cleaned), outputs=[output, report_path, rules_path],
                           message=f"{len(cleaned) / raw_rows:.1%} of {raw_rows:,} raw rows kept, "
                                   f"{batches} batch(es)" if raw_rows else "")

    def _raw_batches(self, raw_path: Path, batches: int):
        """
        Le brut, lot par lot, en DataFrames. En un seul bloc, le fichier est lu tel quel.
        Par lots, DuckDB écrit chaque lot dans `data/<source>/tmp/` puis pandas le relit : les lots
        ont ainsi exactement les mêmes types qu'une lecture en un bloc.
        """
        if batches == 1:
            yield pd.read_parquet(raw_path)
            return
        folder = self.output_dir / TMP / f"clean_batches_{self.tag}"
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        code = "regexp_replace(coalesce(\"code\", ''), '\\s+', '', 'g')"
        con = self.connect()
        try:
            for index in range(batches):
                path = folder / f"batch_{index}.parquet"
                con.execute(
                    f"COPY (SELECT * FROM read_parquet({sql_string(raw_path)}) "
                    f"WHERE hash({code}) % {batches} = {index} ORDER BY ALL) "
                    f"TO {sql_string(path)} (FORMAT PARQUET)")
            con.close()
            con = None
            for index in range(batches):
                path = folder / f"batch_{index}.parquet"
                batch = pd.read_parquet(path)
                path.unlink()
                if len(batch):
                    yield batch
        finally:
            if con is not None:
                con.close()
            shutil.rmtree(folder, ignore_errors=True)

    def load_database(self) -> StepOutcome:
        """
        Nettoyé → base PostgreSQL rechargée en entier (DDL rejoué, une transaction), puis
        contrôle : autant de produits en base que dans le nettoyé. Sans base configurée ou
        joignable, l'étape est ignorée avec un avertissement (sauf `require_db`).
        """
        clean_path = self.resolve(CLEAN)
        credentials = self.db_credentials()
        if credentials is None:
            return self._database_unavailable(
                f"no PostgreSQL password configured ({DB_PASSWORD_ENV}, {DB_PASSWORD_FILE_ENV} "
                f"or {relative_path(self.db_password_file)})"
            )
        try:
            from sqlalchemy import text
            from sqlalchemy.exc import OperationalError

            from .create_database import init_database, load_products
        except ImportError as error:
            return self._database_unavailable(f"database driver not installed ({error})")

        df = pd.read_parquet(clean_path)
        try:
            engine = init_database(CONFIG, **credentials)
        except ImportError as error:          # pilote psycopg absent : chargé par create_engine
            return self._database_unavailable(f"database driver not installed ({error})")
        except OperationalError as error:
            return self._database_unavailable(f"PostgreSQL unreachable ({str(error).splitlines()[0]})")

        try:
            counts = load_products(engine, df)
            with engine.connect() as connection:
                in_database = connection.execute(text("SELECT count(*) FROM products")).scalar_one()
        finally:
            engine.dispose()
        if in_database != len(df):
            raise RuntimeError(f"Database holds {in_database:,} products, cleaned dataset {len(df):,}")

        controls = self.output_dir / "db" / f"load_database_{self.tag}.json"
        write_json({
            "input": clean_path,
            "database": CONFIG["database"]["name"],
            "host": credentials["host"],
            "tables": counts,
            "products_in_database": in_database,
            "products_in_clean": len(df),
        }, controls)
        return StepOutcome(rows=in_database, outputs=[controls])

    def parquet(self) -> StepOutcome:
        """Nettoyé → Parquet partitionné par rayon + schéma + `_SUCCESS` ; même effectif que le nettoyé."""
        clean_path = self.resolve(CLEAN)
        destination = self.dated(PARQUET)
        schema_path = destination.with_name(f"{destination.name}.schema.json")
        to_parquet(clean_path, destination, schema_path)

        written = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = count_rows(clean_path)
        if written["row_count"] != expected:
            raise RuntimeError(f"Parquet holds {written['row_count']:,} products, cleaned dataset {expected:,}")
        return StepOutcome(rows=written["row_count"], outputs=[destination, schema_path],
                           message=f"{len(written['partitions'])} partitions")

    def exports(self) -> StepOutcome:
        """Parquet → export figé daté, avec la colonne `split` et son `schema.json`."""
        source = self.resolve(PARQUET)
        parquet_path, schema_path = export_features(source, self.output_dir / EXPORT.folder,
                                                    force=self.force, freeze_date=self.run_date)
        contract = json.loads(schema_path.read_text(encoding="utf-8"))
        counts = contract["split"]["counts"]
        return StepOutcome(rows=contract["row_count"], outputs=[parquet_path, schema_path],
                           message=f"split {counts['train']:,} train / {counts['test']:,} test, "
                                   f"sha256 {contract['sha256'][:12]}")

    # ------------------------------------------------------------------ base

    def db_credentials(self) -> dict | None:
        """Identifiants PostgreSQL, ou `None` si aucun mot de passe n'est configuré."""
        password = os.environ.get(DB_PASSWORD_ENV)
        if not password:
            password_file = Path(os.environ.get(DB_PASSWORD_FILE_ENV) or self.db_password_file)
            if password_file.is_file():
                password = password_file.read_text(encoding="utf-8").strip()
        if not password:
            return None
        values = {key: os.environ.get(env, default) for key, (env, default) in DB_ENV.items()}
        return {**values, "port": int(values["port"]), "password": password}

    def _database_unavailable(self, reason: str) -> StepOutcome:
        if self.require_db:
            raise RuntimeError(f"Database required (--require-db) but {reason}")
        return StepOutcome(status=SKIPPED,
                           message=f"WARNING: database not loaded: {reason}")

    # ------------------------------------------------------------------ exécution

    def run(self, step: str) -> StepResult:
        """Exécute une étape, la chronomètre et l'inscrit au journal (succès comme échec)."""
        step = ALIASES.get(step, step)
        if step not in STEPS:
            raise ValueError(f"Unknown step {step!r}: expected one of {', '.join(STEPS)}")

        started = datetime.now()
        start = time.perf_counter()
        try:
            outcome = getattr(self, step)()
        except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as error:
            outcome = StepOutcome(status=FAILED, message=f"{type(error).__name__}: {error}")
        except Exception as error:     # erreur inattendue : trace complète, mais journalisée
            traceback.print_exc()
            outcome = StepOutcome(status=FAILED, message=f"{type(error).__name__}: {error}")

        result = StepResult(
            timestamp=started.isoformat(timespec="seconds"),
            run_id=self.run_id,
            run_date=self.tag,
            source=relative_path(self.source),
            name=self.name,
            step=step,
            status=outcome.status,
            duration_s=round(time.perf_counter() - start, 3),
            rows=outcome.rows,
            outputs=[relative_path(path) for path in outcome.outputs],
            message=relative_message(outcome.message),
            options={"batches": self.batches or "auto", "memory": self.memory, "force": self.force},
        )
        self.log(result)
        return result

    def run_all(self) -> list[StepResult]:
        """Enchaîne les cinq étapes ; s'arrête à la première qui échoue."""
        results = []
        for number, step in enumerate(STEPS, start=1):
            self.say(f"\n[{number}/{len(STEPS)}] {step}")
            result = self.run(step)
            results.append(result)
            if result.status == FAILED:
                self.say("Pipeline stopped.")
                break
        return results

    def log(self, result: StepResult) -> None:
        """Ajoute une ligne au journal des durées et l'affiche."""
        journal = self.data_dir / JOURNAL
        journal.parent.mkdir(parents=True, exist_ok=True)
        with open(journal, "a", encoding="utf-8") as file:
            file.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

        rows = f"{result.rows:,} rows" if result.rows is not None else "no rows"
        self.say(f"  {result.status.upper():7s} {result.step}: {rows} in {result.duration_s:.1f} s")
        if result.message:
            self.say(f"          {result.message}")
        for output in result.outputs:
            self.say(f"          -> {output}")

    def say(self, message: str) -> None:
        if self.verbose:
            print(message, flush=True)


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a date as YYYYMMDD, got {value!r}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nutriscope.pipeline",
        description="NutriScope end-to-end pipeline: raw Open Food Facts export -> ML-ready exports.",
    )
    parser.add_argument("step", nargs="?", default="all",
                        choices=[*COMMANDS, *ALIASES],
                        help="Step to run (default: all). French names of the brief are accepted.")
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--source", type=Path, default=None,
                         help=f"Raw CSV/TSV or Parquet source (default: ${SOURCE_ENV}, else the shared sample)")
    sources.add_argument("--full", action="store_true",
                         help=f"Use the full extract {relative_path(FULL_SOURCE)}")
    parser.add_argument("--sep", default=None,
                        help="Source separator, e.g. '\\t' (default: detected from the header)")
    parser.add_argument("--date", type=parse_date, default=None,
                        help="Run date YYYYMMDD, to replay a past date (default: today)")
    parser.add_argument("--force", action="store_true",
                        help="Allow overwriting the frozen export of the run date")
    parser.add_argument("--require-db", action="store_true",
                        help="Fail instead of skipping load_database when PostgreSQL is unavailable")
    parser.add_argument("--data-dir", type=Path, default=DATA_PATH,
                        help="Output root folder: one sub-folder per source, plus logs/ "
                             "(default: data/ of the repository)")
    parser.add_argument("--name", default=None,
                        help="Output sub-folder of the source (default: derived from the source "
                             "file name, e.g. en-openfoodfacts-org-products)")
    parser.add_argument("--batches", type=int, default=None,
                        help=f"Cleaning batches (default: 1, or {DEFAULT_BATCHES} above "
                             f"{AUTO_BATCH_ROWS:,} raw rows; 1 = single block)")
    parser.add_argument("--memory", default=None,
                        help="DuckDB memory limit, e.g. 12GB (default: DuckDB's own, 80%% of RAM)")
    parser.add_argument("--include-exports", action="store_true",
                        help="With purge: also delete the frozen exports")
    parser.add_argument("-a", "--all", action="store_true", dest="all_sources",
                        help="With purge: purge every source, not only the current one")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.all_sources and args.step != "purge":
        parser.error("-a/--all only applies to purge")
    source = Path(FULL_SOURCE if args.full else args.source or os.environ.get(SOURCE_ENV) or DEFAULT_SOURCE)
    try:
        name = check_name(args.name or source_name(source))
    except ValueError as error:
        parser.error(str(error))

    if args.step == "purge":
        removed = purge(args.data_dir, name=None if args.all_sources else name,
                        include_exports=args.include_exports)
        for path in removed:
            print(f"removed {relative_path(path)}")
        scope = "all sources" if args.all_sources else f"source {name}"
        print(f"{len(removed)} pipeline outputs removed ({scope})")
        return 0

    sep = args.sep.encode().decode("unicode-escape") if args.sep else None
    pipeline = Pipeline(
        source=source,
        name=name,
        sep=sep,
        data_dir=args.data_dir,
        run_date=args.date,
        force=args.force,
        require_db=args.require_db,
        batches=args.batches,
        memory=args.memory,
    )
    print(f"NutriScope pipeline - run date {pipeline.tag} - source {relative_path(pipeline.source)} "
          f"- outputs {relative_path(pipeline.output_dir)}")

    if args.step == "all":
        results = pipeline.run_all()
    else:
        results = [pipeline.run(args.step)]

    failed = [result.step for result in results if result.status == FAILED]
    total = sum(result.duration_s for result in results)
    print(f"\n{'FAILED: ' + ', '.join(failed) if failed else 'DONE'} ({total:.1f} s, "
          f"journal {relative_path(pipeline.data_dir / JOURNAL)})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
