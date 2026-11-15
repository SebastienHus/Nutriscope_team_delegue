"""
Le rôle de l'assistant, lu dans ``assistant_behavior.txt`` (à côté du paquet).

Le fichier commence par des réglages ``CLE: valeur``, puis vient le prompt système lui-même ::

    TEMPERATURE: 0
    MAX_TOKENS: 600

    [RÔLE]
    ...

Les réglages inconnus sont ignorés ; le prompt est tout ce qui suit la première ligne vide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BEHAVIOR_PATH = Path(__file__).resolve().parent / "assistant_behavior.txt"
_SETTING = re.compile(r"^([A-Z_]+)\s*:\s*(.+)$")


@dataclass(frozen=True)
class Behavior:
    prompt: str
    temperature: float = 0.0
    max_tokens: int = 600


def load_behavior(path: str | Path = BEHAVIOR_PATH) -> Behavior:
    text = Path(path).read_text(encoding="utf-8")
    settings: dict[str, str] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines) and (match := _SETTING.match(lines[index].strip())):
        settings[match.group(1)] = match.group(2).strip()
        index += 1
    prompt = "\n".join(lines[index:]).strip()
    if not prompt:
        raise ValueError(f"{path}: empty system prompt")
    return Behavior(
        prompt=prompt,
        temperature=float(settings.get("TEMPERATURE", 0)),
        max_tokens=int(settings.get("MAX_TOKENS", 600)),
    )
