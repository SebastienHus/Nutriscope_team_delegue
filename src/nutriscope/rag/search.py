"""
Recherche dans l'index : les morceaux les plus proches d'une question.

La question est vectorisée avec sa consigne (``embed_query``), puis chaque collection demandée est
interrogée séparément, avec son propre ``k`` : les 5 963 fiches ne noient pas les quelques centaines
de morceaux de documents. La question est toujours vectorisée sur le processeur (alias
``num_gpu 0``), quel que soit le matériel qui a servi à l'indexation. Le score est la similarité
cosinus (1 - distance de Chroma), entre -1 et 1.

    from nutriscope.rag.search import search
    hits = search("pâte à tartiner moins sucrée", collection="sheets", k=5)
    hits = search("Nutri-Score", collection="sheets", where={"incomplete_data": False})

    python -m nutriscope.rag.search "comment est calculé le Nutri-Score ?" --collection documents
    python -m nutriscope.rag.search "peu salé" --collection sheets --section Cheese
    python -m nutriscope.rag.search "pâte à tartiner" --no-instruction   # sans la consigne, pour comparer
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Callable

from ..corpus.embeddings import embed_documents, embed_model, embed_model_id, embed_query
from ..options import load_env_file
from .store import COLLECTIONS, DOCUMENTS, SHEETS, chroma_client, open_collection


@dataclass(frozen=True)
class Hit:
    id: str
    collection: str
    score: float                    # similarité cosinus : plus elle est haute, plus c'est proche
    text: str
    metadata: dict = field(default_factory=dict)

    @property
    def citation(self) -> str:
        """Référence courte à citer dans une réponse."""
        meta = self.metadata
        if meta.get("family") == "sheet":
            return f"fiche {meta.get('code')} ({meta.get('source', 'Open Food Facts')})"
        parts = [meta.get("publisher"), meta.get("title")]
        if meta.get("page") is not None:
            parts.append(f"p. {meta['page']}")
        if meta.get("updated"):
            parts.append(f"mis à jour le {meta['updated']}")
        return ", ".join(str(part) for part in parts if part)


def query_collection(collection, name: str, vector: list[float], k: int, where: dict | None) -> list[Hit]:
    result = collection.query(query_embeddings=[vector], n_results=k, where=where or None,
                              include=["documents", "metadatas", "distances"])
    return [Hit(chunk_id, name, round(1 - distance, 4), text, metadata or {})
            for chunk_id, text, metadata, distance in zip(result["ids"][0], result["documents"][0],
                                                          result["metadatas"][0], result["distances"][0])]


def question_vector(question: str, instruction: bool = True) -> list[float]:
    """Vecteur de la question, avec la consigne (défaut) ou brute, comme un document (pour comparer)."""
    if instruction:
        return embed_query(question, model=embed_model())
    return embed_documents([question], model=embed_model())[0]


def search(question: str, collection: str = SHEETS, k: int = 5, where: dict | None = None,
           client=None, embedder: Callable[[str], list[float]] | None = None,
           instruction: bool = True) -> list[Hit]:
    """Les ``k`` morceaux les plus proches de la question, du plus proche au moins proche."""
    vector = embedder(question) if embedder else question_vector(question, instruction)
    client = client or chroma_client()
    return query_collection(open_collection(client, collection, embed_model_id(), create=False), collection,
                            vector, k, where)


def search_all(question: str, k_sheets: int = 5, k_documents: int = 3, where_sheets: dict | None = None,
               client=None, embedder: Callable[[str], list[float]] | None = None,
               instruction: bool = True) -> dict[str, list[Hit]]:
    """Les deux collections, chacune avec son ``k`` ; la question n'est vectorisée qu'une fois.
    ``where_sheets`` ne filtre que les fiches (rayon, Nutri-Score...) : les documents n'ont pas ces champs."""
    vector = embedder(question) if embedder else question_vector(question, instruction)
    client = client or chroma_client()
    return {name: query_collection(open_collection(client, name, embed_model_id(), create=False), name,
                                   vector, k, where)
            for name, k, where in ((SHEETS, k_sheets, where_sheets), (DOCUMENTS, k_documents, None))}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m nutriscope.rag.search",
                                     description="Interroge l'index : morceaux les plus proches d'une question.")
    parser.add_argument("question", help="question en langage naturel")
    parser.add_argument("--collection", choices=(*COLLECTIONS, "both"), default="both",
                        help="collection interrogée (défaut : les deux)")
    parser.add_argument("-k", type=int, default=5, help="nombre de morceaux par collection")
    parser.add_argument("--chars", type=int, default=300, help="caractères affichés par morceau")
    parser.add_argument("--section", default=None,
                        help="filtre sur la métadonnée section (rayon) des fiches, valeur exacte (ex. Cheese)")
    parser.add_argument("--no-instruction", action="store_true",
                        help="vectorise la question sans consigne (pour mesurer ce qu'elle apporte)")
    args = parser.parse_args(argv)
    if args.section and args.collection == DOCUMENTS:
        parser.error("--section only applies to the sheets collection")
    return args


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    args = parse_args(argv)
    where = {"section": args.section} if args.section else None
    instruction = not args.no_instruction
    if args.collection == "both":
        results = search_all(args.question, k_sheets=args.k, k_documents=args.k, where_sheets=where,
                             instruction=instruction)
    else:
        results = {args.collection: search(args.question, args.collection, args.k, where=where,
                                           instruction=instruction)}
    for name, hits in results.items():
        print(f"== {name}")
        for rank, hit in enumerate(hits, start=1):
            preview = " ".join(hit.text.split())[:args.chars]
            print(f"{rank}. {hit.score:.3f}  {hit.id}  [{hit.citation}]\n   {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
