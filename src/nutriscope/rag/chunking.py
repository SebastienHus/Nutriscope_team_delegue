"""
Découpage du corpus en morceaux à indexer.

- **Fiche produit** : un morceau par fiche (``fiche:<code>``), la fiche est déjà courte. Le texte stocké
  est la fiche entière ; le texte vectorisé omet la ligne « Source : », identique sur toutes les
  fiches, qui rapprocherait toutes les fiches les unes des autres sans rien apprendre au modèle.
- **Document de référence** : morceaux d'environ ``MAX_CHARS`` caractères (``doc:<id>:<n>``) faits de
  phrases entières, avec un chevauchement d'environ ``OVERLAP_CHARS`` caractères entre deux morceaux
  voisins. Un morceau ne franchit jamais un marqueur ``[page N]`` : la page citée est exacte.
  Le texte n'est pas réécrit : seuls les retours à la ligne du PDF (coupure physique des lignes)
  deviennent des espaces. Le texte vectorisé est précédé du titre du document, pour situer le morceau.

Seules les sources « autorisées » de ``data/documents/metadata.jsonl`` entrent dans l'index, sauf
avec ``include_unverified`` ; une source exclue n'y entre jamais (docs/ia/corpus.md).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..options import DATA_PATH

SHEETS_DIR = DATA_PATH / "sheets"
DOCUMENTS_DIR = DATA_PATH / "documents"
METADATA_FILE = "metadata.jsonl"

MAX_CHARS = 800
OVERLAP_CHARS = 150
MIN_CHARS = 40          # en dessous, un morceau n'a pas assez de sens (page de garde, page vide)

AUTHORIZED, EXCLUDED = "authorized", "excluded"   # statuts de nutriscope.corpus.scraping
SHEET_SOURCE_PREFIX = "Source : "

PAGE_MARKER = re.compile(r"^\[page (\d+)\]$", re.MULTILINE)
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str                       # texte stocké, renvoyé et cité tel quel
    metadata: dict = field(default_factory=dict)
    embed_text: str | None = None   # texte vectorisé, s'il diffère du texte stocké

    @property
    def to_embed(self) -> str:
        return self.embed_text if self.embed_text is not None else self.text

    @property
    def text_hash(self) -> str:
        """Empreinte du texte vectorisé : un morceau inchangé n'est pas revectorisé."""
        return hashlib.sha256(self.to_embed.encode("utf-8")).hexdigest()[:16]

    @property
    def meta_hash(self) -> str:
        """Empreinte du texte stocké et des métadonnées : s'ils changent seuls, le vecteur est gardé."""
        payload = json.dumps([self.text, self.metadata], sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def stored_metadata(self) -> dict:
        """Métadonnées enregistrées dans Chroma : sans None (refusé par Chroma), avec les deux empreintes."""
        clean = {key: value for key, value in self.metadata.items() if value is not None}
        return {**clean, "text_hash": self.text_hash, "meta_hash": self.meta_hash}


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# ---------- Fiches produits ----------

def sheet_embedding_text(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith(SHEET_SOURCE_PREFIX))


def sheet_chunks(directory: Path = SHEETS_DIR) -> list[Chunk]:
    """Une fiche par ligne de ``metadata.jsonl`` ; une fiche sans fichier texte est ignorée."""
    directory = Path(directory)
    chunks = []
    for meta in read_jsonl(directory / METADATA_FILE):
        path = directory / f"{meta['code']}.txt"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        metadata = {"family": "sheet", **meta}
        chunks.append(Chunk(f"fiche:{meta['code']}", text, metadata, sheet_embedding_text(text)))
    return chunks


# ---------- Documents de référence ----------

def split_pages(text: str) -> list[tuple[int | None, str]]:
    """(page, texte) ; page vaut None pour le texte sans marqueur (pages web)."""
    parts = PAGE_MARKER.split(text)
    sections = [(None, parts[0])] if parts[0].strip() else []
    sections += [(int(number), body) for number, body in zip(parts[1::2], parts[2::2])]
    return sections


def paragraphs(section: str, kind: str) -> list[str]:
    """Page web : une ligne par bloc. PDF : les lignes sont coupées en pleine phrase, la page
    entière forme un seul paragraphe."""
    if kind == "pdf":
        text = " ".join(section.split())
        return [text] if text else []
    return [" ".join(line.split()) for line in section.splitlines() if line.strip()]


def split_long(sentence: str, max_chars: int) -> list[str]:
    """Une « phrase » plus longue qu'un morceau (tableau, liste sans ponctuation) : coupée entre deux mots."""
    pieces, current = [], ""
    for word in sentence.split():
        if current and len(current) + 1 + len(word) > max_chars:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    return pieces + ([current] if current else [])


def render(units: list[tuple[int, str]]) -> str:
    """Phrases d'un même paragraphe séparées par une espace, paragraphes par un retour à la ligne."""
    text = ""
    for index, (paragraph, sentence) in enumerate(units):
        if index:
            text += " " if paragraph == units[index - 1][0] else "\n"
        text += sentence
    return text


def pack(paras: list[str], max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Regroupe les phrases en morceaux d'au plus ``max_chars`` caractères ; chaque nouveau morceau
    reprend les dernières phrases du précédent dans la limite de ``overlap`` caractères."""
    units = [(index, piece)
             for index, paragraph in enumerate(paras)
             for sentence in SENTENCE_END.split(paragraph) if sentence
             for piece in split_long(sentence, max_chars)]
    chunks: list[str] = []
    current: list[tuple[int, str]] = []
    for unit in units:
        if current and len(render(current + [unit])) > max_chars:
            chunks.append(render(current))
            carry: list[tuple[int, str]] = []
            for previous in reversed(current):
                if len(render([previous] + carry)) > overlap:
                    break
                carry.insert(0, previous)
            current = carry if len(render(carry + [unit])) <= max_chars else []
        current.append(unit)
    if current:
        chunks.append(render(current))
    return chunks


def selected(meta: dict, include_unverified: bool) -> bool:
    status = meta.get("status")
    return status != EXCLUDED and (status == AUTHORIZED or include_unverified)


def document_metadata(meta: dict, number: int, page: int | None) -> dict:
    metadata = {"family": "document", "source_id": meta["id"], "chunk": number}
    for key in ("title", "publisher", "url", "updated", "license", "status", "sha256"):
        if meta.get(key) is not None:
            metadata[key] = meta[key]
    if page is not None:
        metadata["page"] = page
    return metadata


def document_chunks(directory: Path = DOCUMENTS_DIR, include_unverified: bool = False,
                    max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> list[Chunk]:
    directory = Path(directory)
    chunks = []
    for meta in read_jsonl(directory / METADATA_FILE):
        path = directory / f"{meta['id']}.txt"
        if not selected(meta, include_unverified) or not path.is_file():
            continue
        number = 0
        for page, section in split_pages(path.read_text(encoding="utf-8")):
            for text in pack(paragraphs(section, meta.get("kind", "html")), max_chars, overlap):
                if len(text) < MIN_CHARS:
                    continue
                chunks.append(Chunk(f"doc:{meta['id']}:{number:04d}", text,
                                    document_metadata(meta, number, page), f"{meta['title']}\n{text}"))
                number += 1
    return chunks
