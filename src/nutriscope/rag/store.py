"""
Accès à la base vectorielle (service chroma de compose.yml, publié sur l'hôte en 8001).

Deux collections, en distance cosinus :

- ``sheets`` : une fiche par produit du catalogue nettoyé ;
- ``documents`` : les morceaux des documents de référence.

Chroma ne calcule aucun embedding (``embedding_function=None``) : les vecteurs viennent d'Ollama
(``nutriscope.corpus.embeddings``). Le nom du modèle est enregistré dans les métadonnées de la
collection, et une collection construite avec un autre modèle est refusée : des vecteurs de deux
modèles différents ne sont pas comparables.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit

SHEETS = "sheets"
DOCUMENTS = "documents"
COLLECTIONS = (SHEETS, DOCUMENTS)
DESCRIPTIONS = {
    SHEETS: "Fiches produits Open Food Facts, une par produit",
    DOCUMENTS: "Morceaux des documents de référence (docs/ia/corpus.md)",
}
DEFAULT_CHROMA_HOST = "http://localhost:8001"


class IndexMismatch(RuntimeError):
    """La collection existe, mais a été construite avec un autre modèle d'embeddings."""


def chroma_host() -> str:
    """Adresse du serveur lue dans CHROMA_HOST (schéma facultatif)."""
    host = (os.getenv("CHROMA_HOST") or DEFAULT_CHROMA_HOST).strip().rstrip("/")
    return host if "://" in host else f"http://{host}"


def chroma_client(host: str | None = None):
    """Client HTTP de Chroma (paquet chromadb-client, importé ici seulement)."""
    import chromadb
    from chromadb.config import Settings

    parts = urlsplit(host or chroma_host())
    secure = parts.scheme == "https"
    return chromadb.HttpClient(host=parts.hostname, port=parts.port or (443 if secure else 80),
                               ssl=secure, settings=Settings(anonymized_telemetry=False))


def open_collection(client, name: str, embed_model: str, create: bool = True):
    """Ouvre (ou crée) une collection et vérifie qu'elle a été construite avec ``embed_model``."""
    if create:
        collection = client.get_or_create_collection(
            name, configuration={"hnsw": {"space": "cosine"}}, embedding_function=None,
            metadata={"embed_model": embed_model, "description": DESCRIPTIONS.get(name, name)})
    else:
        collection = client.get_collection(name, embedding_function=None)
    built_with = (collection.metadata or {}).get("embed_model")
    if built_with != embed_model:
        raise IndexMismatch(f"collection {name!r} was built with {built_with!r}, not {embed_model!r}: "
                            f"rebuild it (python -m nutriscope.rag.index --rebuild)")
    return collection


def drop_collection(client, name: str) -> bool:
    """Supprime la collection si elle existe ; renvoie True si elle existait."""
    if name not in {getattr(item, "name", item) for item in client.list_collections()}:
        return False
    client.delete_collection(name)
    return True
