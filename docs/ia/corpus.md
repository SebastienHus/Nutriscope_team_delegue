# Corpus de l'assistant NutriScope

Ce document liste toutes les sources que le RAG a le droit d'utiliser. Une source n'entre dans le corpus que si sa licence est établie et permet l'usage prévu. Les fichiers eux-mêmes restent hors du dépôt (`data/` est ignoré par Git) ; ils sont régénérés par deux scripts :

| Script | Sortie | Commande |
|---|---|---|
| `src/nutriscope/corpus/sheets.py` | `data/sheets/<code>.txt` + `data/sheets/metadata.jsonl` | `python -m nutriscope.pipeline sheets` (ou `python -m nutriscope.corpus.sheets`) |
| `src/nutriscope/corpus/scraping.py` | `data/documents/<id>.txt`, `data/documents/raw/` (fichiers bruts) + `data/documents/metadata.jsonl` | `python -m nutriscope.corpus.scraping [--include-unverified]` |

La liste des sources du script (`SOURCES` dans `scraping.py`) reprend les identifiants de ce document : les deux se mettent à jour ensemble.

## Famille 1 — fiches produits

| id | titre | éditeur | origine | mis à jour le | consulté le | licence et conditions | utilisé pour |
|---|---|---|---|---|---|---|---|
| `fiche:<code>` | une fiche texte par produit du catalogue nettoyé (5 316 produits, ceux de la base) | Open Food Facts | dernier `data/echantillon_france/clean/products_clean_<date>.parquet` du pipeline, étape `sheets` | export du 2026-10-14 (date du CSV source du pipeline, `--export-date` pour la fixer) | 2026-11-18 | ODbL : créditer Open Food Facts, repartager la base dérivée dans les mêmes conditions | questions produit, comparaison, explication de score |

Règles de la fiche :

- une valeur inconnue s'écrit « non renseigné », **jamais 0**, et sans unité ;
- « Données incomplètes » est un booléen : « oui » dès qu'un champ de la fiche est « non renseigné », sinon « non » ;
- rayon = `pnns_groups_2` (le plus fin), sinon `pnns_groups_1` ; marque = la première de `brands` ;
- Nutri-Score = lettre et score (« D (14) »), la lettre seule si le score manque ;
- `metadata.jsonl` : `code`, `name`, `brand`, `section`, `nutriscore`, `incomplete_data` (booléen JSON), `source` (une ligne par fiche, pour filtrer et citer) ; plus les valeurs brutes dont `chercher_produit` rend sa fiche sans base SQL : `brands`, `quantity`, `pnns_group_1`, `pnns_group_2`, `labels`, `nutriscore_score`, `nova_group`, `*_100g` (`null` si absent).

## Famille 2 — documents de référence

| id | titre | éditeur | URL | mis à jour le | consulté le | licence et conditions | statut | utilisé pour |
|---|---|---|---|---|---|---|---|---|
| `viepub-ns` | Le Nutri-Score en cinq questions | Vie publique (DILA) | https://www.vie-publique.fr/questions-reponses/286134-le-nutri-score-en-cinq-questions | 2025-03-18 (« Dernière modification » de la page) | 2026-11-18 | Licence Ouverte 2.0 : citer « Vie publique » et la date ; ne pas modifier le contenu | autorisé | fonctionnement du Nutri-Score |
| `santefr-ns` | Ce qu'il faut savoir sur le nouveau Nutri-Score | Santé.fr | https://www.sante.fr/ce-quil-faut-savoir-sur-le-nouveau-nutri-score | 2026-10-01 (`article:modified_time`) | 2026-11-18 | CGU de Santé.fr à lire | à vérifier | nouveau calcul, boissons, caractère volontaire |
| `spf-ns` | Nutri-Score | Santé publique France | https://www.santepubliquefrance.fr/determinants-de-sante/nutrition-et-activite-physique/articles/nutri-score | 2026-03-19 (« Mis à jour le » de la page) | 2026-11-18 | mentions légales de santepubliquefrance.fr à lire | à vérifier | composantes du score |
| `pnns-adultes` | Recommandations relatives à l'alimentation, à l'activité physique et à la sédentarité pour les adultes | Santé publique France | https://www.santepubliquefrance.fr/sites/default/files/rdd/document/42466_spf00000619.pdf | document daté de décembre 2018 (couverture) ; fichier PDF modifié le 2023-02-16 | 2026-11-18 | mentions légales de santepubliquefrance.fr à lire | à vérifier | repères de consommation (fruits et légumes, légumes secs, charcuterie, produits laitiers) |
| `ciqual` | Table de composition nutritionnelle des aliments Ciqual | Anses | https://ciqual.anses.fr/ | à relever sur la fiche data.gouv.fr | — | Licence Ouverte : citer la source et la date de mise à jour | autorisé, non retenu | bonus : questions sur des aliments génériques (non indexé) |
| `hcsp-2017` | Avis relatif à la révision des repères alimentaires pour les adultes | HCSP | https://www.hcsp.fr/ | 2017 | — | « doit être diffusé dans sa totalité, sans ajout ni modification » | **exclu** | lien seulement : le découper en morceaux serait le modifier |

## Extraction du texte

- **Pages web** (BeautifulSoup) : on retire scripts, menus, en-têtes, pieds de page, fils d'Ariane et boutons de partage, puis on garde le contenu de `<main>` (ou `<article>`), un bloc par ligne. La date de mise à jour est relevée dans l'ordre : mention visible (« Mis à jour le », « Dernière modification »), balises `meta` (`article:modified_time`…), balise `<time>`.
- **PDF** (pypdf) : texte page par page, précédé d'un marqueur `[page N]` pour que la réponse puisse citer la page. La date relevée est celle des métadonnées du fichier, qui n'est pas la date du document : la reporter à la main (ci-dessus).
- Chaque fichier brut est gardé dans `data/documents/raw/`, avec son empreinte SHA-256 dans `metadata.jsonl` : on sait exactement quelle version a été indexée.
- Le script lit le `robots.txt` de chaque site (les quatre autorisent ces pages au 2026-11-18), attend 2 s entre deux requêtes et relance jusqu'à 4 fois un téléchargement coupé (le PDF fait 10 Mo).

## Décisions

- **Statut « à vérifier ».** Les trois sources de Santé publique France et Santé.fr ne sont téléchargées qu'avec `--include-unverified`, en attendant la lecture de leurs mentions légales par l'équipe. La décision et sa date sont reportées dans la colonne statut, et dans `SOURCES` (`scraping.py`).
- **Vie publique, « ne pas modifier le contenu ».** Le découpage en morceaux ne réécrit pas le texte : chaque morceau garde le texte d'origine mot pour mot, et la réponse cite la page source et sa date. L'équipe considère que ce n'est pas une modification ; si le formateur en juge autrement, la source passe en « lien seulement ».
- **Vie publique, protection anti-robots.** Le site renvoie d'abord une petite page qui pose un cookie et redirige en JavaScript. Le script suit cette redirection une fois, comme le ferait un navigateur (une seule page téléchargée).
- **Lien du PDF PNNS mort.** L'ancien lien (`santepubliquefrance.fr/content/download/197811/2365735`) redirige vers la page d'accueil ; remplacé par l'URL actuelle du PDF (page de présentation : https://www.santepubliquefrance.fr/determinants-de-sante/nutrition-et-activite-physique/documents/rapport-synthese/recommandations-relatives-a-l-alimentation-a-l-activite-physique-et-a-la-sedentarite-pour-les-adultes). Le script refuse une réponse qui n'est pas un PDF.
- **HCSP exclu.** La condition de diffusion intégrale interdit d'en extraire des morceaux. Le lien peut figurer dans la documentation, pas dans le corpus.
- **Ciqual non retenu.** Source tabulaire : elle relève d'un outil de recherche (comme `chercher_produit`), pas d'un découpage en texte. Piste pour la suite.

## Modèles du RAG (service `ollama` de `compose.yml`)

| Rôle | Modèle | Où il tourne | Variable |
|---|---|---|---|
| Embeddings (vectorisation des morceaux et des questions) | `qwen3-embedding:0.6b`, servi sous l'alias `qwen3-embedding-cpu:0.6b` (`num_gpu 0`) | processeur ; GPU possible pour l'indexation en masse (`--device gpu`, ADR 0004) | `OLLAMA_EMBED_MODEL`, `OLLAMA_EMBED_ALIAS`, `OLLAMA_EMBED_THREADS` |
| Juge des réponses (évaluation du TP 20) | Flow-Judge v0.1 3.8B, `hf.co/flowaicom/Flow-Judge-v0.1-GGUF:Q4_K_M` | GPU, llama.cpp arrêté | `OLLAMA_JUDGE_MODEL` |

Client d'embeddings : `nutriscope.corpus.embeddings.embed(textes)`. Évaluation en deux passes : `python -m nutriscope.evaluation generate|judge --version <nom>`. Les choix et les mesures sont dans l'[ADR 0003](../adr/0003-embeddings-et-juge-sur-ollama.md).

Le découpage en morceaux, la vectorisation et l'index Chroma sont décrits dans [rag.md](rag.md) (`python -m nutriscope.rag.index`).
