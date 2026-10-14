"""
Journal des durées : une ligne JSON par étape terminée, succès, saut ou échec
(`data/logs/pipeline_journal.jsonl`). C'est la source des durées citées dans `docs/data/pipeline.md`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

JOURNAL_NAME = "pipeline_journal.jsonl"


def journal_path(settings) -> Path:
    return settings.logs_dir / JOURNAL_NAME


def append(settings, result) -> None:
    path = journal_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "run_date": settings.run_date.isoformat(),
        "step": result.step,
        "status": result.status,
        "seconds": round(result.seconds, 2),
        "rows": result.rows,
        "outputs": result.outputs,
        "message": result.message,
        "source": settings.source.name,
        "batches": settings.batches,
    }
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(line, ensure_ascii=False) + "\n")


def read(settings) -> list[dict]:
    path = journal_path(settings)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
