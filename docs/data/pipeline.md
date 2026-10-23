# Pipeline de données NutriScope — jalon J3

Une commande unique va de l'export Open Food Facts brut aux données prêtes pour le
machine learning. Le code vit dans `src/nutriscope/pipeline.py` ; le `Makefile` n'est
qu'une façade. Installation et prérequis : voir le [README](../../README.md).

Données : © Open Food Facts contributors — ODbL (crédit repris dans chaque manifeste,
schéma et export produit).

## 1. Schéma du flux

```text
 data-nutriscope/echantillon_france.csv          (défaut, versionné)
 data/en.openfoodfacts.org.products.csv          (--full, TSV 13 Go, hors Git)
 $NUTRISCOPE_SOURCE / --source                    (CSV, TSV ou Parquet)
                 │
                 ▼
 ┌────────────────────┐  data/raw/products_raw_<date>.parquet
 │ 1. load            │  data/raw/products_raw_<date>.manifest.json  (SHA-256 source, horodatage)
 └────────────────────┘  code-barres lu en texte, colonnes de database_options.ini
                 │
                 ▼
 ┌────────────────────┐  data/clean/products_clean_<date>.parquet   (trié par code)
 │ 2. clean_data      │  data/clean/cleaning_report_<date>.md       (rapport avant/après)
 └────────────────────┘  data/clean/cleaning_rules_<date>.json      (compte rendu par règle)
                 │
        ┌────────┴──────────────────────────┐   même nettoyé : source de vérité unique
        ▼                                   ▼
 ┌────────────────────┐             ┌────────────────────┐
 │ 3. load_database   │             │ 4. parquet         │
 └────────────────────┘             └────────────────────┘
  PostgreSQL `nutriscope`            data/parquet/products_<date>/pnns_group=<rayon>/data_0.parquet
  (DDL rejoué, une transaction)      data/parquet/products_<date>/_SUCCESS   (écrit en dernier)
  data/db/load_database_<date>.json  data/parquet/products_<date>.schema.json
        │                                   │
        ▼                                   ▼
  APPLICATION                        ┌────────────────────┐
  (fiches produit, comparaison)      │ 5. exports         │
                                     └────────────────────┘
                                      data/exports/features_nutriscore_<date>.parquet  (colonne `split`)
                                      data/exports/features_nutriscore_<date>.schema.json
                                            │
                                            ▼
                                      ANALYSE ET ML (phase 4 : TP 14 à 16)

 Toutes les étapes → data/logs/pipeline_runs.jsonl (journal des durées, échecs compris)
```

| Artefact                         | Écrit par       | Lu par                                      |
| -------------------------------- | --------------- | ------------------------------------------- |
| `raw/products_raw_<date>`        | `load`          | `clean_data`                                |
| `clean/products_clean_<date>`    | `clean_data`    | `load_database`, `parquet`                  |
| base PostgreSQL                  | `load_database` | l'application                               |
| `parquet/products_<date>/`       | `parquet`       | `exports`, notebooks d'analyse (DuckDB)     |
| `exports/features_nutriscore_*`  | `exports`       | phase 4 (modèles)                           |
| `logs/pipeline_runs.jsonl`       | toutes          | ce document (durées)                        |

Garanties :

- **sorties datées** : deux dates cohabitent ; le même jour, une étape réécrit les mêmes
  octets (tri par code, DuckDB sur un seul thread, horodatages dans les manifestes et non
  dans les données) ;
- **résolution des entrées** : chaque étape prend la sortie du jour, sinon la plus récente
  antérieure ; sinon elle échoue en nommant l'étape à lancer avant ;
- **pas de sortie à moitié écrite** : fichiers écrits puis renommés, dossier Parquet
  marqué `_SUCCESS` en dernier, refusé par `exports` sans ce marqueur ;
- **mêmes comptages** : `parquet` et `load_database` vérifient tous deux qu'ils
  contiennent autant de produits que le nettoyé ;
- **base facultative** : sans mot de passe configuré ou sans serveur joignable,
  `load_database` est ignorée avec un avertissement (`--require-db` la rend obligatoire).

## 2. Commandes

| Besoin                                   | Commande                                                     |
| ---------------------------------------- | ------------------------------------------------------------ |
| Tout le pipeline (échantillon)           | `python -m nutriscope.pipeline all` — `make pipeline`        |
| Une étape seule                          | `python -m nutriscope.pipeline <étape>` — `make <étape>`     |
| L'extrait complet                        | `python -m nutriscope.pipeline all --full` — `make extrait`  |
| Une autre source                         | `--source CHEMIN` ou `NUTRISCOPE_SOURCE=CHEMIN`              |
| Rejouer une date                         | `--date AAAAMMJJ` (ajouter `--force` pour réécrire l'export) |
| Exiger la base                           | `--require-db`                                               |
| Les tests                                | `python -m pytest -q` — `make test`                          |
| Tout est cassé                           | `python -m nutriscope.pipeline purge` puis `all` — `make clean pipeline` |
| Supprimer aussi les exports figés        | `python -m nutriscope.pipeline purge --include-exports` — `make clean-all` |

Étapes : `load`, `clean_data`, `load_database`, `parquet`, `exports` (alias de
l'énoncé : `charger`, `nettoyer`, `charger_base`). Code de retour : 0 si aucune étape
n'a échoué, 1 sinon.

L'export est **figé** : relancé le même jour, `exports` échoue avec `FileExistsError`.
C'est voulu. `--force` le réécrit et doit redonner la même empreinte SHA-256 ; une
nouvelle règle de nettoyage se traduit par un nouvel export daté, sans écraser l'ancien.

## 3. Durées mesurées

Les durées viennent du journal `data/logs/pipeline_runs.jsonl`. Pour les résumer :

```bash
python -c "import pandas as pd; j = pd.read_json('data/logs/pipeline_runs.jsonl', lines=True); print(j[j.status != 'failed'].groupby(['run_date', 'step'], sort=False)[['duration_s', 'rows']].last())"
```

Machine : _à compléter (processeur, RAM, disque, OS)_ — Python 3.12.10, pandas 3.0.6,
DuckDB 1.5.6, pyarrow 26.0.0.

| Étape           | Échantillon : lignes | Échantillon : durée | Extrait complet : lignes | Extrait complet : durée |
| --------------- | -------------------- | ------------------- | ------------------------ | ----------------------- |
| `load`          | _à mesurer_          | _à mesurer_         | _à mesurer_              | _à mesurer_             |
| `clean_data`    | _à mesurer_          | _à mesurer_         | _à mesurer_              | _à mesurer_             |
| `load_database` | _à mesurer_          | _à mesurer_         | _à mesurer_              | _à mesurer_             |
| `parquet`       | _à mesurer_          | _à mesurer_         | _à mesurer_              | _à mesurer_             |
| `exports`       | _à mesurer_          | _à mesurer_         | _à mesurer_              | _à mesurer_             |
| **Total**       |                      | _à mesurer_         |                          | _à mesurer_             |

Lecture : _à rédiger une fois les mesures faites — quelle étape domine, pourquoi, et ce
que cela implique (un orchestrateur est-il justifié, ou le `Makefile` suffit-il ?)._

## 4. Ce que la phase 4 lira

**Fichier** : `data/exports/features_nutriscore_<date>.parquet`, une ligne par produit
utilisable (grade a-e, sept nutriments clés présents, cohérences sucres/glucides et
saturés/lipides, énergie > 0), triée par code.

**Contrat** : `features_nutriscore_<date>.schema.json` — date de gel, source, commit Git,
SHA-256, filtres, type, unité, taux de manquants et politique d'imputation de chaque
colonne, répartition des grades, et le bloc `split` :

| Clé                     | Contenu                                                              |
| ----------------------- | -------------------------------------------------------------------- |
| `method`                | stratifié sur `nutriscore_grade`, générateur NumPy local par grade   |
| `seed`, `test_size`     | 42 et 0,2 (lus dans `src/nutriscope/database_options.ini`)           |
| `counts_by_grade`       | effectifs train / test et part de test pour chaque grade             |
| `usage_rule`            | la règle d'usage ci-dessous                                          |

Pourquoi 20 % : avec environ 850 000 produits sur l'extrait complet, même le grade le
plus rare (b, 12 %) garde plus de 20 000 produits de test, assez pour des métriques
stables, sans priver l'entraînement.

**Règle d'usage** : `fit` sur le train seulement ; le test n'est regardé qu'une fois, à
la fin ; la validation croisée se fait à l'intérieur du train.

**Interdits** :

- ne pas recalculer le split : lire la colonne `split` ;
- ne pas utiliser `nutriscore_score` pour prédire le grade (le grade en est dérivé : fuite) ;
- ne pas utiliser `code`, `product_name` ou `brands` comme features ;
- ne pas écraser un export existant : produire un nouvel export daté.

Les notebooks de la phase 4 lisent ces règles via `nutriscope.classification`
(`split_frame`, `check_no_leak`).

## Dette connue

- Le tableau des durées reste à remplir avec des mesures réelles (échantillon puis
  extrait complet).
- L'export du TP 12 ne contient ni `fiber_100g`, ni `fruits-vegetables-legumes_100g`,
  ni `pnns_groups_2`, que le jeu ML partagé (`nutriscope_ml_sample.parquet`) contient :
  les notebooks de la phase 4 lisent pour l'instant le jeu partagé.
