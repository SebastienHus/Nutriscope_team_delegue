"""Tests du RAG : découpage, synchronisation de l'index et recherche (faux Chroma, faux embeddings)."""

import json

import pytest

from nutriscope.corpus import embeddings
from nutriscope.rag import chunking, index, search, store


# ---------- Faux Chroma : juste ce que le pipeline utilise ----------

class FakeCollection:
    def __init__(self, name, metadata):
        self.name, self.metadata, self.rows = name, metadata, {}

    def get(self, include=(), limit=None, offset=0):
        ids = sorted(self.rows)[offset:offset + limit if limit else None]
        return {"ids": ids, "metadatas": [self.rows[i]["metadata"] for i in ids]}

    def upsert(self, ids, embeddings, documents, metadatas):
        for chunk_id, vector, text, metadata in zip(ids, embeddings, documents, metadatas):
            self.rows[chunk_id] = {"vector": vector, "text": text, "metadata": metadata}

    def delete(self, ids):
        for chunk_id in ids:
            self.rows.pop(chunk_id, None)

    def count(self):
        return len(self.rows)

    def query(self, query_embeddings, n_results, where=None, include=()):
        query = query_embeddings[0]
        rows = [(chunk_id, row) for chunk_id, row in self.rows.items()
                if not where or all(row["metadata"].get(key) == value for key, value in where.items())]
        scored = sorted(rows, key=lambda item: -sum(a * b for a, b in zip(item[1]["vector"], query)))
        scored = scored[:n_results]
        return {"ids": [[i for i, _ in scored]], "documents": [[r["text"] for _, r in scored]],
                "metadatas": [[r["metadata"] for _, r in scored]],
                "distances": [[1 - sum(a * b for a, b in zip(r["vector"], query)) for _, r in scored]]}


class FakeClient:
    def __init__(self):
        self.collections = {}

    def get_or_create_collection(self, name, configuration=None, embedding_function=None, metadata=None):
        return self.collections.setdefault(name, FakeCollection(name, metadata))

    def get_collection(self, name, embedding_function=None):
        return self.collections[name]

    def list_collections(self):
        return list(self.collections.values())

    def delete_collection(self, name):
        del self.collections[name]


class CountingEmbedder:
    """Vecteur unitaire selon le premier mot reconnu ; compte les textes vectorisés."""
    WORDS = ("chocolat", "fromage", "nutri")

    def __init__(self):
        self.calls = 0

    def __call__(self, texts):
        self.calls += len(texts)
        return [self.vector(text) for text in texts]

    def vector(self, text):
        lowered = text.lower()
        return [1.0 if word in lowered else 0.0 for word in self.WORDS]


# ---------- Découpage ----------

def test_pack_respects_size_and_overlaps():
    sentences = [f"Phrase numéro {i} qui parle du Nutri-Score." for i in range(40)]
    chunks = chunking.pack([" ".join(sentences)], max_chars=200, overlap=60)
    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)
    for previous, current in zip(chunks, chunks[1:]):
        last_sentence = previous.split(". ")[-1]
        assert current.startswith(last_sentence.rstrip(".")), "le morceau suivant reprend la fin du précédent"
    assert all(chunk.endswith(".") for chunk in chunks), "on ne coupe jamais une phrase"


def test_pack_keeps_paragraphs_and_splits_long_sentences():
    assert chunking.pack(["Titre", "Premier paragraphe."], max_chars=200) == ["Titre\nPremier paragraphe."]
    long_sentence = " ".join(["mot"] * 100)
    assert all(len(chunk) <= 50 for chunk in chunking.pack([long_sentence], max_chars=50, overlap=0))


def test_split_pages():
    text = "[page 1]\nCouverture\n\n[page 2]\nTexte de la page 2"
    assert chunking.split_pages(text) == [(1, "\nCouverture\n\n"), (2, "\nTexte de la page 2")]
    assert chunking.split_pages("Page web sans marqueur") == [(None, "Page web sans marqueur")]


@pytest.fixture
def corpus(tmp_path):
    sheets = tmp_path / "sheets"
    sheets.mkdir()
    for code, name in (("111", "Chocolat noir"), ("222", "Fromage frais")):
        (sheets / f"{code}.txt").write_text(f"Produit : {name}\nCode-barres : {code}\n"
                                            f"Source : Open Food Facts (licence ODbL)", encoding="utf-8")
    metas = [{"code": "111", "name": "Chocolat noir", "incomplete_data": False, "brand": None},
             {"code": "222", "name": "Fromage frais", "incomplete_data": True}]
    (sheets / "metadata.jsonl").write_text("\n".join(json.dumps(m) for m in metas), encoding="utf-8")

    documents = tmp_path / "documents"
    documents.mkdir()
    pdf_text = "[page 1]\nCouverture\n\n[page 2]\nLe Nutri-Score classe les aliments\nde A à E. " * 3
    sources = [
        {"id": "ok", "title": "Le Nutri-Score", "kind": "pdf", "status": "authorized", "url": "u", "pages": 2},
        {"id": "maybe", "title": "Peut-être", "kind": "html", "status": "to_verify"},
        {"id": "never", "title": "Exclu", "kind": "html", "status": "excluded"},
    ]
    (documents / "ok.txt").write_text(pdf_text, encoding="utf-8")
    for source_id in ("maybe", "never"):
        (documents / f"{source_id}.txt").write_text("Un paragraphe assez long pour faire un morceau valable.",
                                                    encoding="utf-8")
    (documents / "metadata.jsonl").write_text("\n".join(json.dumps(s) for s in sources), encoding="utf-8")
    return sheets, documents


def test_sheet_chunks(corpus):
    sheets, _ = corpus
    chunks = chunking.sheet_chunks(sheets)
    assert [chunk.id for chunk in chunks] == ["fiche:111", "fiche:222"]
    assert "Source :" in chunks[0].text and "Source :" not in chunks[0].to_embed
    assert chunks[0].metadata == {"family": "sheet", "code": "111", "name": "Chocolat noir",
                                  "incomplete_data": False}  # None retiré : Chroma le refuse


def test_document_chunks_status_pages_and_text(corpus):
    _, documents = corpus
    chunks = chunking.document_chunks(documents)
    assert {chunk.metadata["source_id"] for chunk in chunks} == {"ok"}
    assert all(chunk.metadata["page"] == 2 for chunk in chunks), "la page de garde est trop courte"
    assert "classe les aliments de A à E." in chunks[0].text, "retours à la ligne du PDF recollés"
    assert chunks[0].to_embed.startswith("Le Nutri-Score\n"), "titre devant le texte vectorisé"
    ids = {chunk.metadata["source_id"] for chunk in chunking.document_chunks(documents, include_unverified=True)}
    assert ids == {"ok", "maybe"}, "une source exclue n'entre jamais"


# ---------- Synchronisation de l'index ----------

def test_sync_is_incremental(corpus):
    sheets, _ = corpus
    collection = FakeCollection("sheets", {})
    embedder = CountingEmbedder()
    chunks = chunking.sheet_chunks(sheets)

    first = index.sync(collection, chunks, embedder, verbose=False)
    assert (first["added"], embedder.calls) == (2, 2)
    assert collection.rows["fiche:111"]["metadata"]["text_hash"] == chunks[0].text_hash

    second = index.sync(collection, chunks, embedder, verbose=False)
    assert (second["unchanged"], embedder.calls) == (2, 2), "rien n'est revectorisé"

    changed = [chunking.Chunk("fiche:111", "Produit : Chocolat au lait", {"code": "111"})]
    third = index.sync(collection, changed, embedder, verbose=False)
    assert (third["updated"], third["deleted"], collection.count()) == (1, 1, 1)


def test_sync_limit_leaves_the_rest_for_later(corpus):
    sheets, _ = corpus
    collection = FakeCollection("sheets", {})
    counts = index.sync(collection, chunking.sheet_chunks(sheets), CountingEmbedder(), limit=1, verbose=False)
    assert (counts["added"], counts["skipped"], collection.count()) == (1, 1, 1)


def test_collection_built_with_another_model_is_refused():
    client = FakeClient()
    store.open_collection(client, "sheets", "model-a")
    with pytest.raises(store.IndexMismatch):
        store.open_collection(client, "sheets", "model-b")
    assert store.drop_collection(client, "sheets") and not store.drop_collection(client, "sheets")


# ---------- Recherche ----------

def test_search_returns_closest_with_citation(corpus, monkeypatch):
    sheets, documents = corpus
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "fake-model")
    client, embedder = FakeClient(), CountingEmbedder()
    for name, chunks in (("sheets", chunking.sheet_chunks(sheets)), ("documents", chunking.document_chunks(documents))):
        index.sync(store.open_collection(client, name, "fake-model"), chunks, embedder, verbose=False)

    hits = search.search("un chocolat", "sheets", k=1, client=client, embedder=embedder.vector)
    assert hits[0].id == "fiche:111" and hits[0].score == pytest.approx(1.0)
    assert hits[0].citation.startswith("fiche 111")

    filtered = search.search("un chocolat", "sheets", k=1, where={"incomplete_data": True},
                             client=client, embedder=embedder.vector)
    assert filtered[0].id == "fiche:222"

    both = search.search_all("le nutri-score", k_sheets=1, k_documents=1, client=client, embedder=embedder.vector)
    assert both["documents"][0].citation == "Le Nutri-Score, p. 2"


def test_query_text_and_model_names(monkeypatch):
    assert embeddings.query_text("Q ?", "Find it") == "Instruct: Find it\nQuery:Q ?"
    monkeypatch.delenv("OLLAMA_EMBED_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_EMBED_ALIAS", raising=False)
    assert embeddings.embed_model() == "qwen3-embedding-cpu:0.6b"
    assert embeddings.embed_model("gpu") == embeddings.embed_model_id() == "qwen3-embedding:0.6b"


def test_chroma_host_parsing(monkeypatch):
    monkeypatch.setenv("CHROMA_HOST", "localhost:8001/")
    assert store.chroma_host() == "http://localhost:8001"
