"""Tests du RAG : découpage, synchronisation de l'index et recherche (faux Chroma, faux embeddings)."""

import json

import pytest

from nutriscope.corpus import embeddings
from nutriscope.rag import chunking, index, retriever, search, store
from nutriscope.tools import ToolContext, ToolRegistry


# ---------- Faux Chroma : juste ce que le pipeline utilise ----------

class FakeCollection:
    def __init__(self, name, metadata):
        self.name, self.metadata, self.rows = name, metadata, {}

    def get(self, ids=None, include=(), limit=None, offset=0):
        if ids is None:
            ids = sorted(self.rows)[offset:offset + limit if limit else None]
        else:
            ids = [i for i in ids if i in self.rows]
        return {"ids": ids, "metadatas": [self.rows[i]["metadata"] for i in ids],
                "embeddings": [self.rows[i]["vector"] for i in ids]}

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
        def accepted(metadata):
            return all(metadata.get(key) in value["$in"] if isinstance(value, dict) else metadata.get(key) == value
                       for key, value in (where or {}).items())
        rows = [(chunk_id, row) for chunk_id, row in self.rows.items() if accepted(row["metadata"])]
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
    stored = chunks[0].stored_metadata()
    assert "brand" not in stored, "None retiré : Chroma le refuse"
    assert {key: stored[key] for key in ("family", "code", "name", "incomplete_data")} == {
        "family": "sheet", "code": "111", "name": "Chocolat noir", "incomplete_data": False}
    assert {"text_hash", "meta_hash"} <= set(stored)


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

    # le filtre ne porte que sur les fiches : les documents n'ont pas ce champ
    both = search.search_all("un chocolat", k_sheets=1, k_documents=1, where_sheets={"incomplete_data": True},
                             client=client, embedder=embedder.vector)
    assert both["sheets"][0].id == "fiche:222" and len(both["documents"]) == 1


def test_section_filter_is_rejected_on_documents():
    assert search.parse_args(["q", "--section", "Cheese"]).section == "Cheese"
    assert search.parse_args(["q", "--no-instruction"]).no_instruction
    with pytest.raises(SystemExit):
        search.parse_args(["q", "--collection", "documents", "--section", "Cheese"])


def test_query_text_and_model_names(monkeypatch):
    assert embeddings.query_text("Q ?", "Find it") == "Instruct: Find it\nQuery:Q ?"
    monkeypatch.delenv("OLLAMA_EMBED_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_EMBED_ALIAS", raising=False)
    assert embeddings.embed_model() == "qwen3-embedding-cpu:0.6b"
    assert embeddings.embed_model("gpu") == embeddings.embed_model_id() == "qwen3-embedding:0.6b"


def test_chroma_host_parsing(monkeypatch):
    monkeypatch.setenv("CHROMA_HOST", "localhost:8001/")
    assert store.chroma_host() == "http://localhost:8001"


def test_metadata_change_keeps_the_vector(corpus):
    sheets, _ = corpus
    collection, embedder = FakeCollection("sheets", {}), CountingEmbedder()
    chunks = chunking.sheet_chunks(sheets)
    index.sync(collection, chunks, embedder, verbose=False)
    retagged = [chunking.Chunk(chunk.id, chunk.text, {**chunk.metadata, "fat_100g": 12.5}, chunk.embed_text)
                for chunk in chunks]
    counts = index.sync(collection, retagged, embedder, verbose=False)
    assert (counts["metadata"], counts["added"] + counts["updated"], embedder.calls) == (2, 0, 2)
    assert collection.rows["fiche:111"]["metadata"]["fat_100g"] == 12.5


def test_build_index_leaves_a_collection_without_corpus_untouched(corpus, tmp_path, monkeypatch):
    sheets, _ = corpus
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "fake-model")
    monkeypatch.setattr(index, "embed_documents", lambda texts, model=None: CountingEmbedder()(texts))
    client = FakeClient()
    store.open_collection(client, "documents", "fake-model").upsert(["doc:x:0000"], [[1, 0, 0]], ["x"], [{}])
    report = index.build_index(sheets_dir=sheets, documents_dir=tmp_path / "absent", client=client, verbose=False)
    assert report["sheets"]["added"] == 2 and report["documents"] == {"missing": True}
    assert client.collections["documents"].count() == 1


# ---------- RagIndex : le catalogue derrière chercher_produit ----------

def sheet_meta(code, name, brands, **values):
    return {"family": "sheet", "code": code, "name": name, "brand": brands.split(",")[0], "brands": brands,
            "nutriscore": "e", "nutriscore_score": 24, "section": "Sweets", **values}


@pytest.fixture
def rag(monkeypatch):
    """Un index de 4 fiches et 1 passage ; vecteur = (chocolat, biscuit, nutri) selon les mots du texte."""
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "fake-model")
    client = FakeClient()
    sheets_col = store.open_collection(client, "sheets", "fake-model")
    rows = [("111", "Pâte à tartiner chocolat", "Choco, Marque", [0.9, 0.1, 0]),
            ("222", "Pâte à tartiner chocolat", "Autre", [0.8, 0.2, 0]),
            ("3000000000333", "Prince goût chocolat", "LU, Prince", [0.5, 0.86, 0]),
            ("0012345678905", "Biscuit nature", "Sablé", [0, 1, 0])]
    for code, name, brands, vector in rows:
        sheets_col.upsert([f"fiche:{code}"], [vector], [name],
                          [sheet_meta(code, name, brands, sugars_100g=56.3, fiber_100g=None)])
    docs = store.open_collection(client, "documents", "fake-model")
    docs.upsert(["doc:viepub-ns:0000"], [[0, 0, 1]], ["Le Nutri-Score classe les aliments de A à E."],
                [{"family": "document", "source_id": "viepub-ns", "title": "Le Nutri-Score en cinq questions",
                  "publisher": "Vie publique (DILA)", "updated": "2025-03-18"}])
    vectors = {"nutella": [0, 0, 0.1], "pate a tartiner": [0.9, 0.1, 0], "prince lu": [0.3, 0.3, 0],
               "chocolat tartinable": [0.95, 0.05, 0], "Comment est calculé le Nutri-Score ?": [0, 0, 1],
               "Quel temps fera-t-il ?": [0.1, 0.1, 0.1]}
    return retriever.RagIndex(client=client, embedder=lambda text: vectors[text])


def test_rag_index_find_by_code_and_upc_variant(rag):
    assert rag.find_by_code("012345678905")[0]["code"] == "0012345678905"   # UPC-A à 12 chiffres
    assert rag.find_by_code("30000000009") == []


def test_rag_index_lexical_then_semantic_then_nothing(rag):
    total, rows = rag.search_by_name(["pate", "a", "tartiner"], 5, query="pate a tartiner")
    assert total == 2 and {row["code"] for row in rows} == {"111", "222"}
    total, rows = rag.search_by_name(["prince", "lu"], 5, query="prince lu")      # score faible, mots présents
    assert (total, rows[0]["code"]) == (1, "3000000000333")
    total, rows = rag.search_by_name(["chocolat", "tartinable"], 5, query="chocolat tartinable")  # repli
    assert (total, rows[0]["code"]) == (1, "111"), "seule la meilleure, à moins de NAME_MARGIN"
    assert rag.search_by_name(["nutella"], 5, query="nutella") == (0, [])


def test_chercher_produit_keeps_its_contract_on_the_rag_index(rag):
    registry = ToolRegistry.discover(ToolContext(catalog=rag, documents=rag))
    assert {"chercher_produit", "chercher_document"} <= set(registry.names)
    result = registry.run("chercher_produit", {"code": "3000000000333"})
    assert result["statut"] == "ok" and result["total"] == 1
    fiche = result["produits"][0]
    assert fiche["nom"] == "Prince goût chocolat" and fiche["marque"] == "LU, Prince"
    assert fiche["nutriscore"] == "E" and fiche["score_nutriscore"] == 24
    assert fiche["nutriments"]["sucres"] == 56.3 and fiche["nutriments"]["fibres"] is None
    assert fiche["donnees_incompletes"] is True
    assert registry.run("chercher_produit", {"nom": "nutella"}) == {"statut": "introuvable", "total": 0,
                                                                    "produits": []}


def test_chercher_document(rag):
    registry = ToolRegistry.discover(ToolContext(catalog=rag, documents=rag))
    result = registry.run("chercher_document", {"question": "Comment est calculé le Nutri-Score ?"})
    assert result["statut"] == "ok" and result["total"] == 1
    passage = result["passages"][0]
    assert passage["editeur"] == "Vie publique (DILA)" and passage["mis_a_jour"] == "2025-03-18"
    assert passage["texte"].startswith("Le Nutri-Score classe")
    far = registry.run("chercher_document", {"question": "Quel temps fera-t-il ?"})
    assert far == {"statut": "introuvable", "total": 0, "passages": []}
    assert "erreur" in registry.run("chercher_document", {"question": "x", "rayon": "y"})
    assert "erreur" in registry.run("chercher_document", {"limite": 2})


def test_document_tool_is_absent_without_documents():
    assert "chercher_document" not in ToolRegistry.discover(ToolContext(catalog=None)).names


def test_default_catalog_is_the_rag_index():
    from nutriscope import catalog
    assert isinstance(catalog.default_catalog(), retriever.RagIndex)   # paresseux : aucun appel réseau


# ---------- lister_produits : plusieurs produits d'un type, classés ----------

@pytest.mark.parametrize("word, text, expected", [
    ("biscuits", "biscuit nature", True), ("biscuit", "biscuits and cakes", True),
    ("gateaux", "gateau basque", True), ("chips", "archipel", False), ("chips", "chipolata", False),
    ("eau", "gateau", False), ("eau", "eaux minerales", True), ("jus", "pur jus", True),
])
def test_word_pattern_whole_word_singular_or_plural(word, text, expected):
    assert bool(retriever.word_pattern(word).search(text)) is expected


@pytest.fixture
def shelf(monkeypatch):
    """5 fiches : 3 biscuits (dont 1 par sa seule catégorie), 1 yaourt, 1 soda ; vecteur = (biscuit, yaourt, soda)."""
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "fake-model")
    client = FakeClient()
    col = store.open_collection(client, "sheets", "fake-model")
    rows = [("1", "Biscuit nature", "Biscuits and cakes", "b", 2, 20.0, [1, 0, 0]),
            ("2", "Sablé au beurre", "Biscuits and cakes", "a", -1, 12.0, [0.9, 0, 0]),
            ("3", "Biscuits fourrés", "Biscuits and cakes", "d", 14, None, [0.95, 0, 0]),
            ("4", "Yaourt nature", "Milk and yogurt", "a", 0, 4.0, [0, 1, 0]),
            ("5", "Cola", "Sweetened beverages", "e", 13, 10.6, [0, 0, 1])]
    for code, name, group, grade, score, sugars, vector in rows:
        col.upsert([f"fiche:{code}"], [vector], [name],
                   [sheet_meta(code, name, "Marque", pnns_group_2=group, nutriscore=grade, nutriscore_score=score,
                               sugars_100g=sugars)])
    vectors = {"biscuits": [1, 0, 0], "boisson gazeuse": [0, 0, 1], "ordinateur": [0.3, 0.3, 0.3]}
    return retriever.RagIndex(client=client, embedder=lambda text: vectors[text])


def test_list_products_by_words_and_category_label(shelf):
    total, rows = shelf.list_products(["biscuits"], "biscuits", None, "nutriscore_score", False, 5)
    assert total == 3 and [row["code"] for row in rows] == ["2", "1", "3"]   # meilleur score d'abord
    total, rows = shelf.list_products(["biscuits"], "biscuits", ["a", "b"], "sugars_100g", False, 5)
    assert [row["code"] for row in rows] == ["2", "1"]
    total, rows = shelf.list_products(["biscuits"], "biscuits", None, "sugars_100g", True, 5)
    assert [row["code"] for row in rows] == ["1", "2", "3"], "valeur non renseignée en dernier"
    assert shelf.list_products(["gateaux"], "gateaux", None, "nutriscore_score", False, 5)[0] == 3


def test_list_products_semantic_fallback_then_nothing(shelf):
    total, rows = shelf.list_products(["boisson", "gazeuse"], "boisson gazeuse", None, "nutriscore_score", False, 5)
    assert (total, rows[0]["code"]) == (1, "5")
    assert shelf.list_products(["ordinateur"], "ordinateur", None, "nutriscore_score", False, 5) == (0, [])


def test_list_products_filters_the_type_found_never_replaces_it(shelf):
    # des yaourts existent, aucun noté E : introuvable, sans repli sémantique (l'embedder ne connaît pas « yaourt »)
    assert shelf.list_products(["yaourt"], "yaourt", ["e"], "nutriscore_score", False, 5) == (0, [])


def test_lister_produits_contract(shelf):
    registry = ToolRegistry.discover(ToolContext(catalog=shelf))
    result = registry.run("lister_produits", {"mots": ["biscuits"], "nutriscore_max": "b", "tri": "sucres"})
    assert (result["statut"], result["total"], result["tri"], result["ordre"]) == ("ok", 2, "sucres", "le moins d'abord")
    first = result["produits"][0]
    assert list(first) == ["rang", "code", "nom", "marque", "nutriscore", "categorie", "nutriments"]
    assert (first["rang"], first["nom"], first["nutriscore"], first["nutriments"]["sucres"]) == (1, "Sablé au beurre", "A", 12.0)
    assert registry.run("lister_produits", {"mots": ["ordinateur"]})["statut"] == "introuvable"
    for bad in ({"mots": ["biscuits"], "limite": 6}, {"mots": ["biscuits"], "nutriscore_max": "F"},
                {"mots": ["biscuits"], "tri": "prix"}, {"mots": ["  "]}, {"mots": []}, {"mots": "biscuits"},
                {"mots": ["a", "b", "c", "d", "e", "f"]}, {"recherche": "biscuits"}, {"nom": "biscuits"}):
        assert "erreur" in registry.run("lister_produits", bad), bad


def test_list_tool_needs_a_catalog_that_can_list():
    from nutriscope.catalog import InMemoryCatalog
    assert "lister_produits" not in ToolRegistry.discover(ToolContext(catalog=InMemoryCatalog([]))).names
