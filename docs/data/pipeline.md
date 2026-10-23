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
 ┌────────────────────┐  data/<source>/raw/products_raw_<date>.parquet         (lu en flux par DuckDB)
 │ 1. load            │  data/<source>/raw/products_raw_<date>.manifest.json  (empreinte source, versions, horodatage)
 └────────────────────┘  tout en texte, colonnes de options.ini
                 │
                 ▼
 ┌────────────────────┐  data/<source>/clean/products_clean_<date>.parquet   (trié par code)
 │ 2. clean_data      │  data/<source>/clean/cleaning_report_<date>.md       (rapport avant/après)
 └────────────────────┘  data/<source>/clean/cleaning_rules_<date>.json      (compte rendu par règle et par lot)
                         en un bloc, ou par lots au-delà d'1 M de lignes (data/<source>/tmp/, effacé après)
                 │
        ┌────────┴──────────────────────────┐   même nettoyé : source de vérité unique
        ▼                                   ▼
 ┌────────────────────┐             ┌────────────────────┐
 │ 3. load_database   │             │ 4. parquet         │
 └────────────────────┘             └────────────────────┘
  PostgreSQL `nutriscope`            data/<source>/parquet/products_<date>/pnns_group=<rayon>/data_0.parquet
  (DDL rejoué, une transaction)      data/<source>/parquet/products_<date>/_SUCCESS   (écrit en dernier)
  data/<source>/db/                  data/<source>/parquet/products_<date>.schema.json
    load_database_<date>.json
        │                                   │
        ▼                                   ▼
  APPLICATION                        ┌────────────────────┐
  (fiches produit, comparaison)      │ 5. exports         │
                                     └────────────────────┘
                                      data/<source>/exports/features_nutriscore_<date>.parquet  (colonne `split`)
                                      data/<source>/exports/features_nutriscore_<date>.schema.json
                                            │
                                            ▼
                                      ANALYSE ET ML (phase 4 : TP 14 à 16)

 Toutes les étapes → data/logs/pipeline_runs.jsonl (journal des durées, échecs compris)
```

**Un dossier par source.** `<source>` est le nom du fichier source sans extension, en
minuscules, chaque suite de caractères spéciaux remplacée par un tiret :

| Source                                         | Dossier de sorties                     |
| ---------------------------------------------- | -------------------------------------- |
| `data-nutriscope/echantillon_france.csv`       | `data/echantillon_france/`             |
| `data/en.openfoodfacts.org.products.csv`       | `data/en-openfoodfacts-org-products/`  |

`--name` force un autre nom (lettres minuscules, chiffres, `_` ou `-`). Les noms `logs`,
`tmp`, `raw`, `clean`, `db`, `parquet`, `exports` et `docs` sont refusés : ce sont le
journal et les dossiers de l'ancienne organisation, où les sorties allaient directement
dans `data/`. Ainsi, l'échantillon et l'extrait complet ne s'écrasent jamais, le même
jour non plus, et chacun a son propre export figé. Le journal des durées reste commun :
chaque ligne indique la source (`source`) et son dossier (`name`).

| Artefact (dans `data/<source>/`) | Écrit par       | Lu par                                      |
| -------------------------------- | --------------- | ------------------------------------------- |
| `raw/products_raw_<date>`        | `load`          | `clean_data`                                |
| `clean/products_clean_<date>`    | `clean_data`    | `load_database`, `parquet`                  |
| base PostgreSQL                  | `load_database` | l'application                               |
| `parquet/products_<date>/`       | `parquet`       | `exports`, notebooks d'analyse (DuckDB)     |
| `exports/features_nutriscore_*`  | `exports`       | phase 4 (modèles)                           |
| `data/logs/pipeline_runs.jsonl`  | toutes          | ce document (durées), commun aux sources    |

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
  `load_database` est ignorée avec un avertissement (`--require-db` la rend obligatoire) ;
- **mémoire bornée** : la lecture et le nettoyage tiennent sur un poste de formation même
  avec l'extrait complet (section suivante).

## 2. Gros volumes : lecture DuckDB et nettoyage par lots

L'extrait complet d'Open Food Facts (13 Go, environ 4,5 millions de lignes, 211 colonnes)
ne tient pas en mémoire avec pandas. Les deux méthodes ci-dessous viennent de la
proposition alternative de Sébastien pour le TP 13 (branche
`origin/tp13-alternative-proposition`, banc d'essai du 14/10). Elles ont été portées
dans `src/nutriscope/pipeline.py` sans changer les règles de nettoyage du TP 9.

### Ce que le banc d'essai a mesuré

Mesures de la branche alternative, sur le fichier complet et un poste de 32 Go de RAM.
Nos durées et nos comptages, mesurés avec ce pipeline, sont en section 4 : mêmes
4 535 553 lignes lues et mêmes 996 637 lignes nettoyées. Les pics de mémoire n'ont pas
été remesurés chez nous ; les chiffres ci-dessous sont ceux de son banc d'essai.

| Étape                       | Ancienne méthode                                  | Nouvelle méthode                       |
| --------------------------- | ------------------------------------------------- | -------------------------------------- |
| Lecture du CSV              | pandas par blocs puis `pd.concat` : saturation RAM | DuckDB en flux : 23 s, 10,7 Go de pic, 4 535 553 lignes, aucune perdue |
| Nettoyage                   | un seul bloc : 14,1 Go de pic                     | 8 lots : 2,5 Go de pic, même résultat  |

### `load` : DuckDB lit la source en flux

- Le CSV (ou le Parquet) est lu par DuckDB et écrit directement en Parquet : rien ne
  passe par pandas, la mémoire reste bornée. `--memory 12GB` plafonne DuckDB, qui
  déborde alors sur disque dans `data/<source>/tmp/duckdb/`.
- Seules les colonnes de `options.ini` sont gardées. Celles qui manquent dans
  la source sont listées dans le manifeste (`columns_missing_in_source`).
- **Tout est lu en texte** (`all_varchar`) : le code-barres garde ses zéros de tête, et
  aucun type n'est deviné. Le typage reste la règle 1 du nettoyage (`type_columns`).
- **Guillemets désactivés pour l'export tabulé.** Quelques fiches d'Open Food Facts
  contiennent un `"` isolé qui, avec les guillemets standards, ferait fusionner des
  lignes ou les ferait rejeter. Le CSV à virgules (échantillon) garde les guillemets.
- Les lignes sont triées sur toutes les colonnes, code en premier (`ORDER BY ALL`) :
  deux exécutions écrivent le même fichier, et la déduplication voit toujours les
  fiches d'un même code dans le même ordre.
- **Empreinte de la source** : SHA-256 complet jusqu'à 1 Go. Au-delà, l'export de 13 Go
  demanderait plusieurs minutes de relecture : le manifeste garde alors la taille, la date
  de modification et le SHA-256 du premier Mo (`source_fingerprint.method`).
- **Versions** : le manifeste note les versions de duckdb, pandas, pyarrow, numpy et
  pandera. L'empreinte d'un Parquet en dépend : deux machines aux versions différentes
  peuvent écrire des octets différents pour les mêmes données.

### `clean_data` : nettoyage par lots

- **Quand** : automatiquement au-delà d'un million de lignes brutes (8 lots), ou à la
  demande avec `--batches N`. L'échantillon reste nettoyé en un seul bloc.
- **Comment** : le lot `i` reçoit les produits dont le code-barres, espaces retirés comme
  le fait `filter_codes`, vérifie `hash(code) % N = i`. Chaque lot est écrit par DuckDB
  dans `data/<source>/tmp/clean_batches_<date>/`, relu par pandas, nettoyé par `cleaning.clean()`,
  puis effacé.
- **Pourquoi le résultat est identique** :
  - toutes les fiches d'un même code tombent dans le même lot, donc la déduplication
    choisit la même fiche qu'en un bloc ;
  - les autres règles du TP 9 travaillent ligne par ligne ;
  - le nettoyé final est trié par code, comme en un bloc ;
  - un contrôle refuse la sortie si un code apparaît deux fois après réunion des lots.
- **Le rapport et les comptes rendus s'additionnent.** `report.summarize_before` résume
  chaque lot brut (lignes, codes distincts, complétude, anomalies) et
  `report.merge_reports` additionne les comptes rendus des règles. Le rapport ne garde
  donc jamais le brut complet en mémoire. `cleaning_rules_<date>.json` détaille les
  effectifs de chaque lot (`per_batch`).
- **Preuve** : le test `test_batched_cleaning_gives_the_same_dataset` nettoie
  l'échantillon en 3 lots et vérifie que le résultat et les totaux par règle sont
  identiques au nettoyage en un bloc.

Ce qui n'a pas été repris de la branche alternative : sa structure de package (le dépôt
est désormais un package `src/nutriscope/`), ses noms en français (convention : le code
en anglais), et son split par `md5(graine:code)` en SQL, équivalent au split NumPy déjà
en place (stratifié, stable produit par produit).

## 3. Commandes

| Besoin                                   | Commande                                                     |
| ---------------------------------------- | ------------------------------------------------------------ |
| Tout le pipeline (échantillon)           | `python -m nutriscope.pipeline all` — `make pipeline`        |
| Une étape seule                          | `python -m nutriscope.pipeline <étape>` — `make <étape>`     |
| L'extrait complet                        | `python -m nutriscope.pipeline all --full` — `make extrait`  |
| Nettoyer en N lots                       | `--batches N` (défaut : 1, ou 8 au-delà d'1 M de lignes)     |
| Plafonner la mémoire de DuckDB           | `--memory 12GB`                                              |
| Une autre source                         | `--source CHEMIN` ou `NUTRISCOPE_SOURCE=CHEMIN`              |
| Rejouer une date                         | `--date AAAAMMJJ` (ajouter `--force` pour réécrire l'export) |
| Exiger la base                           | `--require-db`                                               |
| Les tests                                | `python -m pytest -q` — `make test`                          |
| Changer le dossier de sorties            | `--name NOM` (défaut : nom du fichier source)                |
| Tout est cassé (source courante)         | `python -m nutriscope.pipeline purge` puis `all` — `make clean pipeline` |
| Purger l'extrait complet                 | `python -m nutriscope.pipeline purge --full` — `make clean ARGS=--full` |
| Purger toutes les sources                | `python -m nutriscope.pipeline purge -a` — `make clean-all`  |
| Supprimer aussi les exports figés        | ajouter `--include-exports` — `make clean-all ARGS=--include-exports` |

Avec `make`, les options du pipeline passent par la variable `ARGS` : `make` lit
lui-même tout ce qui commence par un tiret, donc `make clean -a` est refusé, mais
`make clean ARGS=-a` fonctionne. Exemples : `make pipeline ARGS=--full`,
`make exports ARGS="--date 20261014 --force"`.

Étapes : `load`, `clean_data`, `load_database`, `parquet`, `exports` (alias de
l'énoncé : `charger`, `nettoyer`, `charger_base`). Code de retour : 0 si aucune étape
n'a échoué, 1 sinon.

L'export est **figé** : relancé le même jour, `exports` échoue avec `FileExistsError`.
C'est voulu. `--force` le réécrit et doit redonner la même empreinte SHA-256 ; une
nouvelle règle de nettoyage se traduit par un nouvel export daté, sans écraser l'ancien.

## 4. Durées mesurées

Les durées viennent du journal `data/logs/pipeline_runs.jsonl`. Chaque ligne porte
l'identifiant de l'exécution (`run_id`, commun aux cinq étapes d'une même commande), la
source traitée et les options. Pour les résumer :

```bash
python -c "import pandas as pd; j = pd.read_json('data/logs/pipeline_runs.jsonl', lines=True); print(j.groupby(['run_id', 'source', 'step'], sort=False)[['status', 'duration_s', 'rows']].last())"
```

**Machine** : AMD Ryzen 5 3600 (6 cœurs, 12 threads), 32 Go de RAM, Windows 11 Famille.
**Versions** (relevées dans le manifeste de `load`) : Python 3.12.10, DuckDB 1.5.6,
pandas 3.0.6, pyarrow 26.0.0, numpy 2.5.3, pandera 0.34.1.

Mesures du 23/10/2026, sans base PostgreSQL (étape ignorée) :

- échantillon : `data-nutriscope/echantillon_france.csv`, exécution de 16h46, un seul bloc ;
- extrait complet : `data/en.openfoodfacts.org.products.csv`, 13 Go, exécution complète
  de 16h55, nettoyage en 8 lots.

| Étape           | Échantillon : lignes | Échantillon : durée | Extrait complet : lignes | Extrait complet : durée | Part du total complet |
| --------------- | -------------------- | ------------------- | ------------------------ | ----------------------- | --------------------- |
| `load`          | 8 689                | 0,2 s               | 4 535 553                | 16,3 s                  | 8 %                   |
| `clean_data`    | 5 316                | 0,7 s               | 996 637                  | 167,8 s                 | 84 %                  |
| `load_database` | ignorée              | —                   | ignorée                  | —                       | —                     |
| `parquet`       | 5 316                | 0,2 s               | 996 637                  | 12,2 s                  | 6 %                   |
| `exports`       | 4 529                | 0,2 s               | 852 626                  | 3,5 s                   | 2 %                   |
| **Total**       |                      | **1,3 s**           |                          | **199,8 s (3 min 20)**  |                       |

L'exécution précédente sur l'extrait complet (16h51) donne des durées voisines :
`load` 23,6 s (premier accès au fichier, cache disque froid), `clean_data` 169,7 s,
`parquet` 12,4 s. Elle a échoué à `exports` : l'export figé de l'échantillon, produit le
même jour sous le même nom, bloquait celui de l'extrait complet. Cause corrigée depuis :
chaque source a son dossier de sorties (section 1).

**Lecture.**

- **Le nettoyage domine : 84 % du temps.** Les règles du TP 9 sont écrites en pandas et
  s'appliquent ligne à ligne sur 4,5 millions de lignes. Les étapes confiées à DuckDB
  (lecture, Parquet, export) prennent chacune moins de 20 secondes.
- **Le rapport de nettoyage a un coût.** Pour s'additionner d'un lot à l'autre, il
  retype chaque lot brut (`summarize_before`), ce que `clean()` fait déjà. C'est la
  première piste si la durée devient gênante ; elle n'a pas été mesurée.
- **Un orchestrateur ne se justifie pas.** Le flux complet tient en 3 minutes 20 sur un
  poste de formation, l'échantillon en un peu plus d'une seconde. La CLI et le
  `Makefile` suffisent. Un orchestrateur deviendrait utile avec des sources multiples,
  des exécutions planifiées ou des reprises partielles sur plusieurs machines, pas pour
  ce flux.

## 5. Ce que la phase 4 lira

**Fichier** : `data/<source>/exports/features_nutriscore_<date>.parquet`, une ligne par produit
utilisable (grade a-e, sept nutriments clés présents, cohérences sucres/glucides et
saturés/lipides, énergie > 0), triée par code.

**Contrat** : `features_nutriscore_<date>.schema.json` — date de gel, source, commit Git,
SHA-256, filtres, type, unité, taux de manquants et politique d'imputation de chaque
colonne, répartition des grades, et le bloc `split` :

| Clé                     | Contenu                                                              |
| ----------------------- | -------------------------------------------------------------------- |
| `method`                | stratifié sur `nutriscore_grade`, générateur NumPy local par grade   |
| `seed`, `test_size`     | 42 et 0,2 (lus dans `src/nutriscope/options.ini`)           |
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

- Le pic de mémoire de `load` et de `clean_data` n'est pas mesuré par le pipeline : les
  chiffres de la section 2 sont ceux de la branche alternative.
- Les sorties produites avant l'organisation par source (directement dans `data/raw/`,
  `data/clean/`, `data/parquet/`, `data/exports/`, `data/tmp/`) sont nettoyées par
  `purge -a`, sauf les exports figés (`--include-exports`). Les fichiers non datés du
  TP 12 (`data/clean/en.openfoodfacts.org.products.csv`, `data/parquet/products/`,
  `data/exports/features_nutriscore_20261011.*`) restent à supprimer à la main.
- L'export complet du 23/10 compte 852 626 produits, contre 851 314 pour celui du 11/10
  produit par l'ancienne lecture pandas (+1 312). Hypothèse : des lignes que pandas
  perdait sur les guillemets isolés. À vérifier en comparant les codes des deux exports.
- Sur l'extrait complet, vérifier que deux exécutions de `load` donnent le même SHA-256 :
  DuckDB y écrit sur plusieurs threads (le tri `ORDER BY ALL` fixe l'ordre des lignes, le
  test d'idempotence ne le prouve que sur l'échantillon).
- La branche alternative a décidé de garder **tous les pays** (pas de filtre France) ;
  `docs/cadrage/parties/perimetre.md` dit encore « commercialisé en France ». À trancher
  en équipe et à reporter dans les deux documents.
- L'export du TP 12 ne contient ni `fiber_100g`, ni `fruits-vegetables-legumes_100g`,
  ni `pnns_groups_2`, que le jeu ML partagé (`nutriscope_ml_sample.parquet`) contient :
  les notebooks de la phase 4 lisent pour l'instant le jeu partagé.
