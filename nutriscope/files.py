"""
Outils fichiers : empreintes, chemins relatifs, manifestes, recherche de l'entrée datée,
remplacement « atomique » (écrire à côté puis renommer) et marqueur `_SUCCESS`.

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import date, datetime
from pathlib import Path

from nutriscope.config import LICENSE, ROOT

SUCCESS = "_SUCCESS"
FAST_HASH_LIMIT = 1024 ** 3          # au-delà d'1 Go (la source de 12 Go), empreinte « rapide »


class StepError(Exception):
    """Erreur attendue d'une étape : le message dit quoi faire (quelle étape lancer, quelle variable définir)."""


# ---------------------------------------------------------------------------- empreintes
def sha256_file(path: Path, block: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(block), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(path: Path) -> dict:
    """SHA-256 complet pour un fichier raisonnable ; pour un très gros fichier, taille + date + SHA-256 du 1er Mo."""
    size = path.stat().st_size
    if size <= FAST_HASH_LIMIT:
        return {"method": "sha256", "value": sha256_file(path), "bytes": size}
    with open(path, "rb") as file:
        head = hashlib.sha256(file.read(1024 * 1024)).hexdigest()
    return {"method": "fast (taille + mtime + sha256 du 1er Mo)", "value": head, "bytes": size,
            "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}


def tree_hashes(directory: Path) -> dict[str, str]:
    """Empreinte de chaque fichier d'un dossier (pour vérifier qu'une relance ne change rien)."""
    return {p.relative_to(directory).as_posix(): sha256_file(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


# ---------------------------------------------------------------------------- chemins
def rel(path: Path) -> str:
    """Chemin relatif au dépôt quand c'est possible : aucun chemin de poste dans les fichiers produits."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def ensure_inside(path: Path, base: Path) -> None:
    """Garde-fou avant toute suppression : on ne supprime jamais hors du dossier de données."""
    path, base = Path(path).resolve(), Path(base).resolve()
    if path == base or base not in path.parents:
        raise StepError(f"Suppression refusée : {path} n'est pas à l'intérieur de {base}")


def remove(path: Path, base: Path) -> None:
    if not Path(path).exists():
        return
    ensure_inside(path, base)
    if Path(path).is_dir():
        shutil.rmtree(path)
    else:
        Path(path).unlink()


def publish(tmp: Path, final: Path, base: Path) -> None:
    """Remplace `final` par `tmp` (fichier ou dossier). La sortie finale n'existe que complète."""
    if final.exists():
        remove(final, base)
    os.replace(tmp, final)


# ---------------------------------------------------------------------------- entrées datées
def dated(directory: Path, prefix: str, suffix: str) -> list[tuple[str, Path]]:
    """Sorties `prefix<AAAAMMJJ>suffix` d'un dossier, triées par date croissante."""
    if not directory.is_dir():
        return []
    pattern = re.compile(re.escape(prefix) + r"(\d{8})" + re.escape(suffix) + r"$")
    found = []
    for path in directory.iterdir():
        match = pattern.match(path.name)
        if match:
            found.append((match.group(1), path))
    return sorted(found)


def find_input(directory: Path, prefix: str, suffix: str, stamp: str, producer: str,
               what: str, need_success: bool = False) -> Path:
    """
    L'entrée d'une étape : la sortie du jour si elle existe, sinon la plus récente.
    Un dossier sans `_SUCCESS` est ignoré (écriture interrompue). Rien trouvé → message utile.
    """
    candidates = [(s, p) for s, p in dated(directory, prefix, suffix)
                  if not need_success or (p / SUCCESS).is_file()]
    for s, p in candidates:
        if s == stamp:
            return p
    if candidates:
        return candidates[-1][1]
    raise StepError(f"Aucun {what} trouvé dans {rel(directory)} : lancez d'abord "
                    f"« python -m nutriscope.pipeline {producer} ».")


# ---------------------------------------------------------------------------- JSON
def _default(value):
    if isinstance(value, (Path,)):
        return rel(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):          # entiers et flottants numpy
        return value.item()
    return str(value)


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=_default) + "\n", encoding="utf-8")
    return path


def manifest(step: str, settings, outputs: dict, extra: dict | None = None) -> dict:
    """Manifeste commun : l'horodatage et les versions vont ici, jamais dans les fichiers de données."""
    from importlib import metadata

    def version(name):
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            return None

    return {
        "step": step,
        "run_date": settings.run_date.isoformat(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "outputs": outputs,
        **(extra or {}),
        "versions": {name: version(name) for name in ("duckdb", "pandas", "pyarrow", "numpy", "pandera")},
        "license": LICENSE,
    }
