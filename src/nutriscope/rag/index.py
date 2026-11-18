"""
Indexation du corpus dans Chroma : ``python -m nutriscope.rag.index``.

Synchronise chaque collection avec le corpus sur le disque :

- un morceau nouveau ou modifié (empreinte ``text_hash`` différente) est vectorisé puis enregistré ;
- un morceau inchangé n'est pas revectorisé : relancer la commande ne coûte presque rien ;
- un morceau qui a disparu du corpus est supprimé de l'index.

Les vecteurs sont enregistrés lot par lot : une indexation interrompue reprend là où elle s'est
arrêtée. Prérequis : services ollama et chroma démarrés, fiches (``nutriscope.corpus.sheets``) et
documents (``nutriscope.corpus.scraping``) générés.

    python -m nutriscope.rag.index                        # les deux collections
    python -m nutriscope.rag.index --only documents --include-unverified
    python -m nutriscope.rag.index --device gpu           # indexation en masse, ~7 fois plus rapide
    python -m nutriscope.rag.index --limit 200            # essai : au plus 200 morceaux vectorisés
    python -m nutriscope.rag.index --rebuild              # repart de zéro (changement de modèle)
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Callable, Sequence

from ..corpus.embeddings import BATCH_SIZE, embed_documents, embed_model, embed_model_id
from ..options import load_env_file
from .chunking import DOCUMENTS_DIR, SHEETS_DIR, Chunk, document_chunks, sheet_chunks
from .store import COLLECTIONS, SHEETS, chroma_client, drop_collection, open_collection

PAGE_SIZE = 1000   # lecture de l'index existant par pages

Embedder = Callable[[Sequence[str]], list[list[float]]]


def existing_hashes(collection) -> dict[str, str]:
    """{id: text_hash} des morceaux déjà indexés."""
    hashes: dict[str, str] = {}
    offset = 0
    while True:
        page = collection.get(include=["metadatas"], limit=PAGE_SIZE, offset=offset)
        for chunk_id, metadata in zip(page["ids"], page["metadatas"]):
            hashes[chunk_id] = (metadata or {}).get("text_hash", "")
        if len(page["ids"]) < PAGE_SIZE:
            return hashes
        offset += PAGE_SIZE


def sync(collection, chunks: list[Chunk], embedder: Embedder, batch_size: int = BATCH_SIZE,
         limit: int | None = None, verbose: bool = True) -> dict[str, int]:
    """Met la collection en accord avec ``chunks`` ; renvoie le décompte des opérations."""
    ids = [chunk.id for chunk in chunks]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate chunk ids")
    indexed = existing_hashes(collection)
    stale = sorted(set(indexed) - set(ids))
    for start in range(0, len(stale), PAGE_SIZE):
        collection.delete(ids=stale[start:start + PAGE_SIZE])

    todo = [chunk for chunk in chunks if indexed.get(chunk.id) != chunk.text_hash]
    skipped = 0
    if limit is not None and len(todo) > limit:
        skipped, todo = len(todo) - limit, todo[:limit]
    counts = {"added": sum(chunk.id not in indexed for chunk in todo),
              "updated": sum(chunk.id in indexed for chunk in todo),
              "unchanged": len(chunks) - len(todo) - skipped, "deleted": len(stale), "skipped": skipped}

    start_time = time.perf_counter()
    for start in range(0, len(todo), batch_size):
        batch = todo[start:start + batch_size]
        vectors = embedder([chunk.to_embed for chunk in batch])
        collection.upsert(ids=[chunk.id for chunk in batch], embeddings=vectors,
                          documents=[chunk.text for chunk in batch],
                          metadatas=[{**chunk.metadata, "text_hash": chunk.text_hash} for chunk in batch])
        if verbose:
            done = start + len(batch)
            elapsed = time.perf_counter() - start_time
            print(f"  {done}/{len(todo)} embedded ({elapsed:.0f} s, "
                  f"~{elapsed / done * (len(todo) - done):.0f} s left)", flush=True)
    counts["seconds"] = round(time.perf_counter() - start_time, 1)
    return counts


def load_chunks(name: str, args: argparse.Namespace) -> list[Chunk]:
    if name == SHEETS:
        return sheet_chunks(args.sheets_dir)
    return document_chunks(args.documents_dir, include_unverified=args.include_unverified)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m nutriscope.rag.index",
                                     description="Vectorise le corpus et synchronise l'index Chroma.")
    parser.add_argument("--only", choices=COLLECTIONS, help="une seule collection (défaut : les deux)")
    parser.add_argument("--sheets-dir", type=Path, default=SHEETS_DIR, help="dossier des fiches produits")
    parser.add_argument("--documents-dir", type=Path, default=DOCUMENTS_DIR,
                        help="dossier des documents de référence")
    parser.add_argument("--include-unverified", action="store_true",
                        help="indexe aussi les sources « à vérifier » (jamais les sources exclues)")
    parser.add_argument("--limit", type=int, help="vectorise au plus N morceaux par collection (essai)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="textes par appel à Ollama")
    parser.add_argument("--device", choices=("cpu", "gpu"), default="cpu",
                        help="cpu : alias num_gpu 0, ~0,8 s par fiche ; gpu : modèle de base, ~0,1 s par "
                             "fiche et ~2 Go de mémoire graphique (tient à côté de llama.cpp, de justesse)")
    parser.add_argument("--rebuild", action="store_true",
                        help="supprime la collection avant de la reconstruire (changement de modèle)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    args = parse_args(argv)
    model_id, model = embed_model_id(), embed_model(args.device)
    client = chroma_client()
    embedder: Embedder = lambda texts: embed_documents(texts, model=model)  # noqa: E731
    for name in ([args.only] if args.only else COLLECTIONS):
        chunks = load_chunks(name, args)
        print(f"{name}: {len(chunks)} chunks (model {model_id}, called as {model})")
        if args.rebuild and drop_collection(client, name):
            print(f"  collection {name!r} dropped")
        collection = open_collection(client, name, model_id)
        counts = sync(collection, chunks, embedder, batch_size=args.batch_size, limit=args.limit)
        print(f"  added {counts['added']}, updated {counts['updated']}, unchanged {counts['unchanged']}, "
              f"deleted {counts['deleted']}, left for a next run {counts['skipped']} "
              f"({counts['seconds']} s); {collection.count()} in the index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
