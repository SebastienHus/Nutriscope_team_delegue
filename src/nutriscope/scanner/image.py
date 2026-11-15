"""Photo -> URL ``data:`` pour un modèle de vision (le modèle ne peut pas ouvrir un fichier du disque)."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Any

DEFAULT_MAX_SIDE = 1200          # pixels ; les photos du lot font 1 200 px au plus
JPEG_QUALITY = 90


class UnreadableImage(ValueError):
    """Pas une image, ou un chemin qui n'existe pas."""


def image_bytes(image: Any) -> bytes:
    """Accepte un chemin (str ou Path) ou les octets de l'image."""
    if isinstance(image, (bytes, bytearray, memoryview)):
        return bytes(image)
    if isinstance(image, (str, os.PathLike)):
        path = Path(image)
        if not path.is_file():
            raise UnreadableImage(f"fichier introuvable : {path.name}")
        return path.read_bytes()
    raise UnreadableImage(f"type d'image non pris en charge : {type(image).__name__}")


def to_data_url(image: Any, max_side: int | None = None) -> tuple[str, tuple[int, int]]:
    """(URL data: d'un JPEG réduit à ``max_side`` pixels au plus, (largeur, hauteur) envoyées)."""
    from PIL import Image, UnidentifiedImageError

    max_side = max_side or int(os.getenv("SCANNER_MAX_SIDE") or DEFAULT_MAX_SIDE)
    raw = image_bytes(image)
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            img = img.convert("RGB")
            img.thumbnail((max_side, max_side))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
            size = img.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnreadableImage(f"image illisible ({type(exc).__name__})") from None
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}", size
