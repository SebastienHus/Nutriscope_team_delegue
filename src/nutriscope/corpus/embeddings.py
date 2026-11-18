"""
Client d'embeddings du RAG (service ollama de compose.yml, ADR 0003).

Le modèle par défaut est ``OLLAMA_EMBED_ALIAS`` (``qwen3-embedding-cpu:0.6b``) : la variante créée
par ``ollama-init`` avec ``num_gpu 0``, pour que la vectorisation ne prenne jamais de mémoire
graphique à llama.cpp.

    from nutriscope.corpus.embeddings import embed_documents, embed_query
    vectors = embed_documents(["Produit : ...", "Le Nutri-Score ..."])  # un vecteur de 1024 réels par texte
    question = embed_query("Combien de fruits et légumes par jour ?")

qwen3-embedding est asymétrique : la question est précédée d'une consigne (« Instruct: ... » puis
« Query:... » à la ligne, format de la fiche du modèle, consigne en anglais même pour une question en
français), les documents sont vectorisés tels quels. Ollama renvoie des vecteurs déjà normalisés (norme 1).
"""

from __future__ import annotations

import os
from typing import Sequence

import requests

from ..assistant.config import ollama_host

DEFAULT_EMBED_MODEL = "qwen3-embedding:0.6b"
DEFAULT_EMBED_ALIAS = "qwen3-embedding-cpu:0.6b"
BATCH_SIZE = 32
TIMEOUT = 300
# Un morceau fait au plus ~300 tokens : 2048 suffit et coûte moins de mémoire que les 4096 par défaut.
# Toujours la même valeur, sinon Ollama recharge le modèle à chaque changement.
CONTEXT_TOKENS = 2048
QUERY_INSTRUCTION = "Given a question about food products or nutrition, retrieve the passage that answers it"


def embed_model_id() -> str:
    """Identité du modèle, enregistrée dans l'index : les mêmes poids, que l'appel passe par l'alias
    processeur ou par le modèle de base sur le GPU (vecteurs identiques à 1e-3 près)."""
    return os.getenv("OLLAMA_EMBED_MODEL") or DEFAULT_EMBED_MODEL


def embed_model(device: str = "cpu") -> str:
    """Nom à appeler : l'alias ``num_gpu 0`` sur le processeur (défaut), le modèle de base sur le GPU
    (indexation en masse : ~7 fois plus rapide, ~2 Go de mémoire graphique ; tient à côté de llama.cpp,
    de justesse sur 8 Go)."""
    if device == "gpu":
        return embed_model_id()
    return os.getenv("OLLAMA_EMBED_ALIAS") or DEFAULT_EMBED_ALIAS


def embed(texts: Sequence[str], model: str | None = None, batch_size: int = BATCH_SIZE,
          session: requests.Session | None = None) -> list[list[float]]:
    """Un vecteur par texte, dans le même ordre. Lève une exception sur erreur du serveur
    (modèle absent, serveur arrêté)."""
    model = model or embed_model()
    http = session or requests.Session()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = list(texts[start:start + batch_size])
        response = http.post(f"{ollama_host()}/api/embed", json={"model": model, "input": batch,
                                                                    "options": {"num_ctx": CONTEXT_TOKENS}},
                             timeout=TIMEOUT)
        response.raise_for_status()
        result = response.json()["embeddings"]
        if len(result) != len(batch):
            raise RuntimeError(f"{len(batch)} texts sent, {len(result)} vectors received")
        vectors.extend(result)
    return vectors


# Les documents (fiches, morceaux) se vectorisent sans consigne.
embed_documents = embed


def query_text(question: str, instruction: str = QUERY_INSTRUCTION) -> str:
    """La question telle que qwen3-embedding l'attend : consigne, puis question."""
    return f"Instruct: {instruction}\nQuery:{question}"


def embed_query(question: str, instruction: str = QUERY_INSTRUCTION, model: str | None = None,
                session: requests.Session | None = None) -> list[float]:
    """Le vecteur d'une question, consigne comprise."""
    return embed([query_text(question, instruction)], model=model, session=session)[0]
