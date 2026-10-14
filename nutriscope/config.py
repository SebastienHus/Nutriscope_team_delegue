"""
Configuration du pipeline.

Tout se règle par variables d'environnement (compatible avec un futur conteneur) ou par options de
la CLI, avec des valeurs par défaut sûres. Aucun chemin absolu n'est écrit en dur : tout part de
l'emplacement de ce fichier (`ROOT`), jamais du dossier courant.

| Variable                   | Défaut                                        | Rôle                                   |
|----------------------------|-----------------------------------------------|----------------------------------------|
| NUTRISCOPE_SOURCE          | data-nutriscope/echantillon_france.csv        | CSV (ou Parquet) source                |
| NUTRISCOPE_SEP             | détecté (tabulation ou virgule)               | séparateur de la source                |
| NUTRISCOPE_DATA            | <racine>/data                                 | dossier des sorties (hors Git)         |
| NUTRISCOPE_DATE            | aujourd'hui, fuseau Europe/Paris              | date des sorties (AAAAMMJJ)            |
| NUTRISCOPE_BATCHES         | 8                                             | lots du nettoyage (1 = un seul bloc)   |
| NUTRISCOPE_DUCKDB_MEMORY   | 12GB                                          | plafond mémoire de DuckDB              |
| NUTRISCOPE_DUCKDB_THREADS  | tous les cœurs                                | threads DuckDB (étape charger)         |
| NUTRISCOPE_SKIP            | (vide)                                        | étapes à sauter, séparées par virgules |
| NUTRISCOPE_GIT_COMMIT      | lu avec `git`                                 | commit à inscrire dans les schémas     |
| DB_HOST / DB_PORT          | localhost / 5432                              | PostgreSQL (étape charger_base)        |
| DB_USER / DB_PASSWORD      | postgres / (aucun)                            | identifiants, jamais demandés hors terminal |

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data-nutriscope" / "echantillon_france.csv"
LICENSE = "© Open Food Facts contributors — Open Database License (ODbL) 1.0"
TIMEZONE = "Europe/Paris"
SEED = 42                       # graine du split, écrite aussi dans le schéma de l'export
TEST_FRACTION = 0.20            # part de test par grade
DEFAULT_BATCHES = 8             # mesuré : 2,5 Go de pic sur 4,5 M de lignes (banc d'essai du 14/10)
DEFAULT_DUCKDB_MEMORY = "12GB"  # mesuré : 10,7 Go de pic au chargement du fichier complet
STEP_NAMES = ("charger", "nettoyer", "charger_base", "parquet", "exports")


def today_paris() -> date:
    """Date du jour à Paris (un conteneur est souvent en UTC : sans ça, la date change avant minuit)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(TIMEZONE)).date()
    except Exception:  # paquet tzdata absent : on garde la date locale de la machine
        return date.today()


def parse_date(value: str) -> date:
    """« 20261014 » ou « 2026-10-14 » → date."""
    return datetime.strptime(value.strip().replace("-", ""), "%Y%m%d").date()


def detect_separator(path: Path) -> str:
    """Tabulation si la première ligne en contient plus que de virgules (export OFF complet), sinon virgule."""
    if path.suffix.lower() == ".parquet" or not path.is_file():
        return ","
    with open(path, "rb") as file:
        first = file.readline().decode("utf-8", errors="replace")
    return "\t" if first.count("\t") > first.count(",") else ","


def _path(value: str | None, default: Path) -> Path:
    """Chemin donné par l'utilisateur (relatif au dossier courant) ou défaut (relatif au dépôt)."""
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    source: Path
    run_date: date
    sep: str | None = None                  # None = détecté sur la première ligne de la source
    batches: int = DEFAULT_BATCHES
    duckdb_memory: str = DEFAULT_DUCKDB_MEMORY
    duckdb_threads: int | None = None
    skip: tuple[str, ...] = ()
    seed: int = SEED
    test_fraction: float = TEST_FRACTION
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str | None = None
    git_commit: str | None = None

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_env(cls, **overrides) -> "Settings":
        """Lit l'environnement, puis applique les options non nulles (`overrides`, venant de la CLI ou des tests)."""
        env = os.environ
        skip = tuple(s.strip() for s in env.get("NUTRISCOPE_SKIP", "").split(",") if s.strip())
        threads = env.get("NUTRISCOPE_DUCKDB_THREADS")
        settings = cls(
            data_dir=_path(env.get("NUTRISCOPE_DATA"), ROOT / "data"),
            source=_path(env.get("NUTRISCOPE_SOURCE"), DEFAULT_SOURCE),
            run_date=parse_date(env["NUTRISCOPE_DATE"]) if env.get("NUTRISCOPE_DATE") else today_paris(),
            sep=env.get("NUTRISCOPE_SEP") or None,
            batches=int(env.get("NUTRISCOPE_BATCHES", DEFAULT_BATCHES)),
            duckdb_memory=env.get("NUTRISCOPE_DUCKDB_MEMORY", DEFAULT_DUCKDB_MEMORY),
            duckdb_threads=int(threads) if threads else None,
            skip=skip,
            db_host=env.get("DB_HOST", "localhost"),
            db_port=int(env.get("DB_PORT", 5432)),
            db_user=env.get("DB_USER", "postgres"),
            db_password=env.get("DB_PASSWORD") or None,
            git_commit=env.get("NUTRISCOPE_GIT_COMMIT") or None,
        )
        values = {k: v for k, v in overrides.items() if v is not None}
        for key in ("data_dir", "source"):
            if key in values:
                values[key] = _path(str(values[key]), getattr(settings, key))
        return replace(settings, **values)

    # ------------------------------------------------------------------ dérivés
    @property
    def stamp(self) -> str:
        return self.run_date.strftime("%Y%m%d")

    @property
    def separator(self) -> str:
        sep = self.sep if self.sep is not None else detect_separator(self.source)
        return sep.encode().decode("unicode_escape") if "\\" in sep else sep

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def clean_dir(self) -> Path:
        return self.data_dir / "clean"

    @property
    def db_dir(self) -> Path:
        return self.data_dir / "db"

    @property
    def parquet_dir(self) -> Path:
        return self.data_dir / "parquet"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"
