"""Tests des scripts du corpus du RAG : fiches produits et extraction du texte (sans réseau)."""

import json

import pandas as pd

from nutriscope.corpus import scraping, sheets


def product(**overrides) -> pd.Series:
    row = {
        "code": "0012345678905", "product_name": "Le Goût Primeur", "brands": "Savencia, St Moret",
        "pnns_groups_1": "Milk and dairy products", "pnns_groups_2": "Cheese",
        "nutriscore_grade": "d", "nutriscore_score": 14.0, "energy-kcal_100g": 205.0,
        "fat_100g": 17.8, "saturated-fat_100g": 13.2, "sugars_100g": 3.0, "salt_100g": 1.2,
        "fiber_100g": float("nan"), "proteins_100g": 8.3,
    }
    row.update(overrides)
    return pd.Series(row)


def test_sheet_contains_formatted_values():
    text = sheets.product_to_sheet(product(), "2026-10-06")
    assert "Produit : Le Goût Primeur — Savencia" in text
    assert "Code-barres : 0012345678905" in text
    assert "Nutri-Score : D (14)" in text
    assert "matières grasses 17,8 g" in text
    assert "sucres 3 g" in text
    assert "export du 2026-10-06" in text


def test_unknown_value_is_never_zero():
    text = sheets.product_to_sheet(product(sugars_100g=None), "2026-10-06")
    assert "sucres non renseigné ;" in text
    assert "fibres non renseigné ;" in text
    assert "Données incomplètes : oui\n" in text


def test_missing_grade_and_section():
    row = product(nutriscore_grade="unknown", pnns_groups_2="unknown", pnns_groups_1="unknown")
    text = sheets.product_to_sheet(row, "2026-10-06")
    assert "Nutri-Score : non renseigné" in text
    assert "Rayon : non renseigné" in text
    assert sheets.is_incomplete(row)


def test_complete_product():
    row = product(fiber_100g=2.0)
    assert "Données incomplètes : non\n" in sheets.product_to_sheet(row, "2026-10-06")
    assert sheets.product_metadata(row, "2026-10-06")["incomplete_data"] is False


def test_write_sheets_and_metadata(tmp_path):
    df = pd.DataFrame([product(), product(code="3017620422003", fiber_100g=2.0)])
    (tmp_path / "stale.txt").write_text("old")
    assert sheets.write_sheets(df, tmp_path, "2026-10-06") == 2
    assert not (tmp_path / "stale.txt").exists()
    assert (tmp_path / "3017620422003.txt").read_text(encoding="utf-8").startswith("Produit :")
    lines = (tmp_path / sheets.METADATA_FILE).read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    assert {key: first[key] for key in ("code", "name", "brand", "section", "nutriscore", "incomplete_data",
                                        "source")} == {
        "code": "0012345678905", "name": "Le Goût Primeur", "brand": "Savencia", "section": "Cheese",
        "nutriscore": "d", "incomplete_data": True, "source": "Open Food Facts (licence ODbL), export du 2026-10-06"}
    # valeurs brutes pour la fiche de chercher_produit : nombres, toutes les marques, None si absent
    assert first["brands"] == "Savencia, St Moret" and first["nutriscore_score"] == 14
    assert first["fat_100g"] == 17.8 and first["fiber_100g"] is None and first["quantity"] is None


def test_read_catalogue_accepts_pipeline_parquet(tmp_path):
    path = tmp_path / "products_clean_20261116.parquet"
    pd.DataFrame([product(code="0012345678905", quantity="200 g")]).to_parquet(path)
    df = sheets.read_catalogue(path)
    assert df.loc[0, "code"] == "0012345678905" and df.loc[0, "quantity"] == "200 g"


HTML = """<html><head><meta property="article:modified_time" content="2026-10-01T16:58:43+02:00"></head>
<body><header><nav>Accueil | Menu</nav></header>
<main><div class="breadcrumb">Accueil &gt; Nutrition</div>
<h1>Le Nutri-Score</h1><p>Mis à jour le 19 mars 2026</p>
<p>Le Nutri-Score   classe les aliments<br>de A à E.</p>
<ul><li>Fibres</li><li>Protéines</li></ul>
<script>track()</script><div class="share-buttons">Partager</div></main>
<footer>Mentions légales</footer></body></html>"""


def test_html_main_text_drops_navigation_and_scripts():
    text = scraping.html_main_text(HTML)
    assert text.splitlines()[0] == "Le Nutri-Score"
    assert "Le Nutri-Score classe les aliments" in text
    assert "Fibres\nProtéines" in text
    for noise in ("Menu", "Accueil", "track()", "Partager", "Mentions légales"):
        assert noise not in text


def test_updated_date_prefers_visible_mention():
    assert scraping.html_updated_date(HTML) == "2026-03-19"
    assert scraping.html_updated_date(HTML.replace("Mis à jour le 19 mars 2026", "")) == "2026-10-01"
    assert scraping.parse_french_date("1er août 2025") == "2025-08-01"
    assert scraping.parse_french_date("18/03/2025") == "2025-03-18"


def test_excluded_and_unverified_sources_are_skipped():
    ids = {source.id for source in scraping.select_sources(None, include_unverified=False)}
    assert ids == {"viepub-ns"}
    ids = {source.id for source in scraping.select_sources(None, include_unverified=True)}
    assert "hcsp-2017" not in ids and "pnns-adultes" in ids
