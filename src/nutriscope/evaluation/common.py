"""Chemins et fonctions CSV communs aux deux passes de l'évaluation."""

from __future__ import annotations

import csv
from pathlib import Path

from ..options import ROOT_PATH

QUESTIONS_PATH = ROOT_PATH / "eval" / "questions.csv"
RESULTS_DIR = ROOT_PATH / "results" / "eval"
HISTORY_FILE = "history.csv"

# Colonnes de eval/questions.csv. La passe de génération ne lit jamais que QUESTION_COLUMNS.
QUESTION_COLUMNS = ("id", "type", "question")
TRUTH_COLUMNS = ("expected_answer", "expected_sources", "expected_behavior")
BEHAVIORS = ("answer", "refuse", "say_not_found")


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as handle:  # utf-8-sig : fichiers enregistrés par Excel
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_csv(path: Path, row: dict, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.is_file()
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        if new:
            writer.writeheader()
        writer.writerow(row)


def load_questions(path: Path, with_truth: bool, ids: list[str] | None = None) -> list[dict[str, str]]:
    """Questions du jeu d'évaluation. ``with_truth=False`` retire les réponses attendues : la passe
    de génération ne peut pas les glisser dans un prompt, même par erreur."""
    rows = read_csv(path)
    needed = QUESTION_COLUMNS + (TRUTH_COLUMNS if with_truth else ())
    missing = [column for column in needed if rows and column not in rows[0]]
    if missing:
        raise SystemExit(f"{path}: missing column(s) {', '.join(missing)} (expected: {', '.join(needed)})")
    ids_seen = [row["id"] for row in rows]
    if len(set(ids_seen)) != len(ids_seen):
        raise SystemExit(f"{path}: duplicate question ids")
    if with_truth:
        wrong = {row["expected_behavior"] for row in rows} - set(BEHAVIORS)
        if wrong:
            raise SystemExit(f"{path}: unknown expected_behavior {sorted(wrong)} (expected: {', '.join(BEHAVIORS)})")
    if ids:
        rows = [row for row in rows if row["id"] in ids]
    keep = needed if with_truth else QUESTION_COLUMNS
    return [{column: row[column] for column in keep} for row in rows]


def answers_path(results_dir: Path, version: str) -> Path:
    return results_dir / f"{version}_answers.csv"


def judged_path(results_dir: Path, version: str) -> Path:
    return results_dir / f"{version}_judged.csv"
