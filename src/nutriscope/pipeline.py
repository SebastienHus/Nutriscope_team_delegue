"""
Pipeline bout-en-bout NutriScope — TP 13 (jalon J3).

Une commande unique va du CSV Open Food Facts brut aux données prêtes pour le ML, en cinq
étapes lançables séparément. Chaque étape résout elle-même son entrée (la sortie datée du
jour, sinon la plus récente), écrit des sorties datées `<AAAAMMJJ>` et consigne une ligne
dans le journal des durées `data/logs/pipeline_runs.jsonl`, y compris en cas d'échec.

| Étape           | Entrée               | Sortie (dans `data/`)                                        |
| --------------- | -------------------- | ------------------------------------------------------------ |
| `load`          | CSV ou Parquet brut  | `raw/products_raw_<date>.parquet` + `.manifest.json`         |
| `clean_data`    | brut                 | `clean/products_clean_<date>.parquet` + rapport + règles     |
| `load_database` | nettoyé              | base PostgreSQL rechargée + `db/load_database_<date>.json`   |
| `parquet`       | nettoyé              | `parquet/products_<date>/` (par rayon, `_SUCCESS`) + schéma  |
| `exports`       | Parquet              | `exports/features_nutriscore_<date>.parquet` + `.schema.json` |

`load_database` et `parquet` partent du même nettoyé (source de vérité unique) et
vérifient tous deux que leur nombre de produits est celui du nettoyé. Sans PostgreSQL
configuré, `load_database` est ignorée avec un avertissement (`--require-db` la rend
obligatoire). Les noms de l'énoncé (`charger`, `nettoyer`, `charger_base`) sont acceptés.

    python -m nutriscope.pipeline all                       # échantillon partagé
    python -m nutriscope.pipeline exports                   # une étape seule
    python -m nutriscope.pipeline all --full                # extrait complet (data/)
    python -m nutriscope.pipeline exports --date 20261014 --force
    python -m nutriscope.pipeline purge [--include-exports]

Données : © Open Food Facts contributors — ODbL.
"""

import argparse
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
from .reader import CHUNKSIZE, read_products
from .report import generate_report
from .storage.convert_parquet import LICENSE, is_complete, relative_path, sql_string, to_parquet
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
    run_date: str
    step: str
    status: str
    duration_s: float
    rows: int | None
    outputs: list[str]
    message: str


# ============================================================================
# OUTILS
# ============================================================================

def detect_separator(path: Path) -> str:
    """Séparateur d'un export CSV, déduit de sa ligne d'en-tête (tabulation ou virgule)."""
    with open(path, encoding="utf-8", errors="replace") as file:
        header = file.readline()
    return "\t" if header.count("\t") > header.count(",") else ","


def read_source(path: Path, columns: list[str], sep: str | None = None,
                chunksize: int = CHUNKSIZE) -> pd.DataFrame:
    """Lit la source brute (CSV/TSV par blocs, ou Parquet), code-barres en texte."""
    if path.suffix == ".parquet":
        available = duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet({sql_string(path)})").fetchall()
        names = [row[0] for row in available]
        df = pd.read_parquet(path, columns=[column for column in columns if column in names])
        return df.astype({"code": str}) if "code" in df.columns else df
    return read_products(path, columns, sep=sep or detect_separator(path), chunksize=chunksize)


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


def count_rows(path: Path) -> int:
    """Nombre de lignes d'un fichier Parquet."""
    return duckdb.sql(f"SELECT count(*) FROM read_parquet({sql_string(path)})").fetchone()[0]


def purge(data_dir: Path = DATA_PATH, include_exports: bool = False) -> list[Path]:
    """
    Supprime les sorties datées du pipeline et retourne les chemins supprimés.

    Ne touche ni aux sources (`data/*.csv`), ni aux anciens fichiers non datés, ni au
    journal des durées. Les exports figés ne sont supprimés qu'avec `include_exports`.
    """
    targets = [*PURGEABLE, PURGEABLE_EXPORTS] if include_exports else list(PURGEABLE)
    removed = []
    for folder, pattern in targets:
        directory = Path(data_dir) / folder
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
                 require_db: bool = False, chunksize: int = CHUNKSIZE,
                 db_password_file: Path = DEFAULT_DB_PASSWORD_FILE, verbose: bool = True):
        self.source = Path(source or os.environ.get(SOURCE_ENV) or DEFAULT_SOURCE)
        self.sep = sep
        self.data_dir = Path(data_dir)
        self.run_date = run_date or date.today()
        self.force = force
        self.require_db = require_db
        self.chunksize = chunksize
        self.db_password_file = Path(db_password_file)
        self.verbose = verbose

    # ------------------------------------------------------------------ chemins

    @property
    def tag(self) -> str:
        return self.run_date.strftime(DATE_FORMAT)

    def dated(self, artifact: Artifact) -> Path:
        """Chemin de l'artefact pour la date d'exécution."""
        return self.data_dir / artifact.folder / f"{artifact.prefix}{self.tag}{artifact.suffix}"

    def resolve(self, artifact: Artifact) -> Path:
        """
        Entrée d'une étape : l'artefact daté du jour d'exécution, sinon le plus récent
        antérieur. Lève `MissingInputError` en nommant l'étape à lancer avant. Un dossier
        Parquet sans `_SUCCESS` est une écriture interrompue : il est refusé.
        """
        directory = self.data_dir / artifact.folder
        pattern = artifact.pattern()
        candidates = sorted(
            (match.group(1), path)
            for path in (directory.iterdir() if directory.is_dir() else [])
            if (match := pattern.match(path.name)) and match.group(1) <= self.tag
        )
        if not candidates:
            raise MissingInputError(
                f"No {artifact.description} dated {self.tag} or earlier in {directory}: "
                f"run the `{artifact.producer}` step first."
            )
        path = candidates[-1][1]
        if artifact is PARQUET and not is_complete(path):
            raise MissingInputError(
                f"{path} is incomplete (no _SUCCESS marker, interrupted run): "
                f"run the `{artifact.producer}` step again."
            )
        return path

    # ------------------------------------------------------------------ étapes

    def load(self) -> StepOutcome:
        """Source brute → `raw/products_raw_<date>.parquet` + manifeste (empreinte de la source)."""
        if not self.source.is_file():
            raise MissingInputError(
                f"Source not found: {self.source}. Put the Open Food Facts export there, "
                f"pass --source, or set {SOURCE_ENV}."
            )
        sep = self.sep or (detect_separator(self.source) if self.source.suffix != ".parquet" else None)
        df = read_source(self.source, CONFIG["columns"], sep=sep, chunksize=self.chunksize)
        output = self.dated(RAW)
        write_parquet(df, output)

        manifest = output.with_suffix(".manifest.json")
        write_json({
            "step": "load",
            "source": relative_path(self.source),
            "source_sha256": sha256(self.source),
            "source_bytes": self.source.stat().st_size,
            "separator": sep,
            "rows": len(df),
            "columns": list(df.columns),
            "output": relative_path(output),
            "output_sha256": sha256(output),
            "created_at": datetime.now().isoformat(timespec="seconds"),   # horodatage : ici, pas dans les données
            "git_commit": git_commit(),
            "license": LICENSE,
        }, manifest)
        return StepOutcome(rows=len(df), outputs=[output, manifest])

    def clean_data(self) -> StepOutcome:
        """Brut → nettoyé (règles du TP 9, dans l'ordre) + rapport Markdown + journal des règles."""
        raw_path = self.resolve(RAW)
        raw = pd.read_parquet(raw_path)
        cleaned, reports = clean(raw, DEFAULT_STRATEGY)
        cleaned = cleaned.sort_values("code", kind="stable").reset_index(drop=True)

        output = self.dated(CLEAN)
        write_parquet(cleaned, output)

        report_path = output.with_name(f"cleaning_report_{self.tag}.md")
        report_path.write_text(generate_report(raw, cleaned, reports, source=raw_path.name),
                               encoding="utf-8")
        rules_path = output.with_name(f"cleaning_rules_{self.tag}.json")
        write_json({
            "input": raw_path,
            "output": output,
            "rows_before": len(raw),
            "rows_after": len(cleaned),
            "rules": [asdict(report) for report in reports],
            "license": LICENSE,
        }, rules_path)
        return StepOutcome(rows=len(cleaned), outputs=[output, report_path, rules_path],
                           message=f"{len(cleaned) / len(raw):.1%} of {len(raw):,} raw rows kept"
                           if len(raw) else "")

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

        controls = self.data_dir / "db" / f"load_database_{self.tag}.json"
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
        parquet_path, schema_path = export_features(source, self.data_dir / EXPORT.folder,
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
            run_date=self.tag,
            step=step,
            status=outcome.status,
            duration_s=round(time.perf_counter() - start, 3),
            rows=outcome.rows,
            outputs=[relative_path(path) for path in outcome.outputs],
            message=outcome.message,
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
                        help="Output root folder (default: data/ of the repository)")
    parser.add_argument("--chunksize", type=int, default=CHUNKSIZE,
                        help="Rows per block when reading a CSV")
    parser.add_argument("--include-exports", action="store_true",
                        help="With purge: also delete the frozen exports")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.step == "purge":
        removed = purge(args.data_dir, include_exports=args.include_exports)
        for path in removed:
            print(f"removed {relative_path(path)}")
        print(f"{len(removed)} pipeline outputs removed")
        return 0

    sep = args.sep.encode().decode("unicode-escape") if args.sep else None
    pipeline = Pipeline(
        source=FULL_SOURCE if args.full else args.source,
        sep=sep,
        data_dir=args.data_dir,
        run_date=args.date,
        force=args.force,
        require_db=args.require_db,
        chunksize=args.chunksize,
    )
    print(f"NutriScope pipeline - run date {pipeline.tag} - source {relative_path(pipeline.source)}")

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
