# Pipeline de données NutriScope — TP 13 (jalon J3)

> Document de référence pour la phase 4 (machine learning, à partir du 20/10).
> Branche : `tp13-alternative-proposition`. Données : © Open Food Facts contributors — ODbL.

## 1. Le flux

```
                                  python -m nutriscope.pipeline all
                                                │
 CSV Open Food Facts ──► [1 charger] ──► data/raw/produits_bruts_<date>.parquet       (texte, 41 colonnes, trié par code)
 (échantillon 8 689 lignes            │        + manifeste (empreinte de la source)
  ou export complet 4,5 M)            ▼
                               [2 nettoyer] ──► data/clean/produits_propres_<date>.parquet   ◄── SOURCE DE VÉRITÉ UNIQUE
                               règles du TP 9,        + rapport_nettoyage_<date>.md + regles_<date>.json
                               en 8 lots              │
                         ┌────────────────────────────┴───────────────────────────┐
                         ▼                                                        ▼
                 [3 charger_base]                                           [4 parquet]
           PostgreSQL « nutriscope »                          data/parquet/produits_<date>/produits/pnns_group=<rayon>/
           + data/db/base_<date>.json                          + schema_products.json + _SUCCESS
           LU PAR : l'application / l'API                     LU PAR : analyse (DuckDB), EDA, exports
           (accès par code-barres)                                             │
                                                                               ▼
                                                                         [5 exports]
                                                  data/exports/features_nutriscore_<date>.parquet  (+ colonne split)
                                                  + features_nutriscore_<date>.schema.json
                                                  LU PAR : TP 14, 15, 16 (entraînement et évaluation des modèles)

 Toutes les étapes ──► data/logs/pipeline_journal.jsonl  (une ligne par étape : durée, statut, lignes, échecs compris)
```

| Artefact | Produit par | Lu par | Dans Git ? |
|---|---|---|---|
| CSV source | Open Food Facts (téléchargé) | `charger` | non (sauf l'échantillon de test) |
| Brut figé `raw/` | `charger` | `nettoyer` | non |
| Nettoyé `clean/` | `nettoyer` | `charger_base` **et** `parquet` | non |
| Base PostgreSQL | `charger_base` | application / API | non |
| Parquet par rayon | `parquet` | `exports`, notebooks, contrôles DuckDB | non |
| Export features + schéma | `exports` | phase 4 (ML) | non (régénérable) |
| Journal des durées | toutes les étapes | ce document | non |

La base sert l'application (accès par clé) ; le Parquet sert l'analyse et le ML (balayages). Les deux partent du
**même** nettoyé : leurs comptages sont égaux, sinon c'est la chaîne qui est fausse.

## 2. Les étapes

| Étape | Entrée | Sortie | Garanties |
|---|---|---|---|
| `charger` | CSV ou Parquet source | brut Parquet + manifeste | lecture en flux (DuckDB), code-barres en texte, empreinte de la source, tri par code |
| `nettoyer` | brut | nettoyé + rapport + règles | règles du TP 9 inchangées et dans l'ordre ; lots par `hash(code)` ; codes uniques |
| `charger_base` | nettoyé | base + comptes | rechargement complet (DDL rejoué), une transaction, contrôle produits = nettoyé |
| `parquet` | nettoyé | Parquet partitionné + schéma + `_SUCCESS` | types posés, tri, un thread (mêmes octets), pas de dossier à moitié écrit |
| `exports` | Parquet complet (`_SUCCESS`) | features + `split` + schéma | filtres du TP 12, split stratifié graine 42, figé (`--force` pour réécrire) |

Chaque étape retrouve seule son entrée : celle du jour, sinon la plus récente ; sinon elle s'arrête avec
« lancez d'abord … ». Chaque étape peut être relancée : elle réécrit les mêmes octets pour les mêmes données
(l'horodatage est dans les manifestes, pas dans les données).

## 3. Les commandes

| Besoin | Commande |
|---|---|
| Commande unique | `python -m nutriscope.pipeline all` |
| Sans PostgreSQL | `python -m nutriscope.pipeline all --skip charger_base` |
| Une étape seule | `python -m nutriscope.pipeline <charger|nettoyer|charger_base|parquet|exports>` |
| Extrait complet | `python -m nutriscope.pipeline all --source data/en.openfoodfacts.org.products.csv` |
| Rejouer une date | `python -m nutriscope.pipeline exports --date 20261014 --force` |
| État | `python -m nutriscope.pipeline status` |
| Tests | `python -m pytest -q` |
| Tout est cassé | `python -m nutriscope.pipeline clean` puis `python -m nutriscope.pipeline all` |

Façade Makefile (Linux/macOS) : `make pipeline`, `make pipeline-sans-base`, `make <étape>`, `make test`, `make clean`.

Réglages (variables d'environnement, utilisables telles quelles dans un futur conteneur) :
`NUTRISCOPE_SOURCE`, `NUTRISCOPE_SEP`, `NUTRISCOPE_DATA`, `NUTRISCOPE_DATE`, `NUTRISCOPE_BATCHES` (8),
`NUTRISCOPE_DUCKDB_MEMORY` (12GB), `NUTRISCOPE_SKIP`, `NUTRISCOPE_GIT_COMMIT`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`.

## 4. Les durées

Machine de mesure : Windows 11, 16 cœurs logiques, 32 Go de RAM ; Python 3.12.10, DuckDB 1.5.6, pandas 2.3.3,
pyarrow 26.0.0, pandera 0.34.1.

| Étape | Échantillon (8 689 lignes) | Extrait complet (4 535 553 lignes) |
|---|---|---|
| `charger` | _à reporter du journal_ | **23 s** (banc d'essai), pic 10,7 Go |
| `nettoyer` (8 lots) | _à reporter du journal_ | **3 min 08 s** (banc d'essai), pic 2,5 Go → 996 637 lignes |
| `nettoyer` (1 bloc, pour comparaison) | — | 2 min 27 s, pic 14,1 Go |
| `charger_base` | _à reporter du journal_ | _à mesurer_ |
| `parquet` | _à reporter du journal_ | _à mesurer_ |
| `exports` | _à reporter du journal_ | _à mesurer_ |

Les valeurs « banc d'essai » viennent de `docs/tp13/banc_essai/JOURNAL_DEMARCHE.md` (mêmes méthodes,
scripts de mesure séparés). Les autres cases se remplissent avec `data/logs/pipeline_journal.jsonl`
(`python -m nutriscope.pipeline status`), jamais avec des estimations.

Lecture (à confirmer avec les mesures du pipeline) : le nettoyage pandas domine (≈ 85 % du temps sur le fichier
complet) ; le chargement DuckDB est négligeable. Le flux complet tient en quelques minutes : un orchestrateur
(Airflow, Prefect) n'est pas justifié, la CLI et sa façade Makefile suffisent.

## 5. Ce que la phase 4 lira

- **Fichier** : `data/exports/features_nutriscore_<AAAAMMJJ>.parquet` (le plus récent, ou la date figée choisie).
- **Contrat** : `features_nutriscore_<AAAAMMJJ>.schema.json` — colonnes, types, unités, % de manquants,
  politique de manquants prévue, filtres, SHA-256, commit Git, graine, effectifs train/test **par grade**.
- **Cible** : `nutriscore_grade` (a-e). Cible secondaire de régression : `nutriscore_score`.
- **Colonne `split`** : `train` / `test`, 20 % de test **dans chaque grade**, graine 42.
  Méthode : dans chaque grade, produits rangés par `md5('42:' || code)` puis par code ; les `round(0,2 × n)` premiers
  sont `test`. L'affectation d'un produit ne dépend que de son code.

**Règles d'usage (non négociables)**
1. `fit` sur le train seulement ; le test n'est regardé qu'une fois, à la fin.
2. La validation croisée se fait à l'intérieur du train.
3. Ne jamais recalculer le split : utiliser la colonne telle quelle.
4. Ne pas utiliser `nutriscore_score` pour prédire le grade (fuite de cible : le grade en est dérivé).
5. Ne pas utiliser `code`, `product_name` ni `brands` comme features.
6. Toute nouvelle règle de nettoyage → nouvelle date d'export, sans écraser l'ancien : on sait quel modèle a été
   entraîné sur quelles données (nom du fichier + SHA-256).

## 6. Périmètre et décisions

- **Tous les pays** (décision du 14/10/2026) : aucun filtre géographique. S'écarte du critère « commercialisé en
  France » du cadrage TP 2 (`docs/cadrage/parties/perimetre.md`).
- Volumes de référence (export complet du 14/10) : brut 4 535 553 → nettoyé 996 637.
- Le split est fait **après** les filtres de l'export : il ne contient que des produits utilisables (grade a-e,
  sept nutriments clés, cohérences).

## 7. Prêt pour un conteneur (non activé)

Configuration 100 % par variables d'environnement, chemins calculés depuis le dépôt, aucune saisie au clavier
hors terminal, date en fuseau Europe/Paris, commit Git transmissible (`NUTRISCOPE_GIT_COMMIT`), données dans
`data/` (volume). Brouillons : `docs/tp13/conteneurisation/`.
