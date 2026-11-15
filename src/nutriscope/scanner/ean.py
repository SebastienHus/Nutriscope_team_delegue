"""Clé de contrôle des codes-barres (EAN-13, EAN-8, UPC-A) : un chiffre mal lu ne garde presque jamais une clé valide."""

from __future__ import annotations

import re

VALID_LENGTHS = (8, 12, 13)


def clean_barcode(text: object) -> str | None:
    """Chiffres d'un code-barres lu sur une étiquette ("3 017620 422003" -> "3017620422003"), ou None."""
    if text is None:
        return None
    digits = re.sub(r"[\s-]", "", str(text))
    return digits if digits.isdigit() else None


def check_digit(body: str) -> int:
    """Clé des codes GS1 : poids 3 et 1 en partant de la droite, clé elle-même exclue."""
    total = sum(int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(body)))
    return (10 - total % 10) % 10


def is_valid_barcode(code: str | None) -> bool:
    return (code is not None and code.isdigit() and len(code) in VALID_LENGTHS
            and check_digit(code[:-1]) == int(code[-1]))
