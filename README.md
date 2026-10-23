# NutriScope

Comparer les valeurs nutritionnelles de produits à partir de leur code-barres, et prédire
le Nutri-Score des produits qui n'en ont pas. Ce dépôt contient le code qui produit les
données (nettoyage, base, Parquet, exports ML) et les notebooks d'analyse ; il ne
contient jamais les données produites.

Données : Open Food Facts — **© Open Food Facts contributors — ODbL**.

## Prérequis

| Outil      | Version                                   | Obligatoire ?                                              |
| ---------- | ----------------------------------------- | ---------------------------------------------------------- |
| Python     | 3.12 (testé avec 3.12.10)                 | oui                                                        |
| Git        | toute version récente                     | oui                                                        |
| PostgreSQL | 16 ou plus, joignable depuis le poste     | non : sans base, l'étape `load_database` est ignorée       |
| `make`     | GNU make                                  | non : toutes les commandes existent en `python -m ...`     |
| Disque     | ~20 Mo pour l'échantillon, ~20 Go pour l'extrait complet | —                                           |

## Installation

Toutes les commandes se lancent **depuis la racine du dépôt** (le dossier qui contient
`pyproject.toml`).

```powershell
# Windows (PowerShell)
git clone <url-du-depot> nutriscope
cd nutriscope
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

```bash
# Linux / macOS
git clone <url-du-depot> nutriscope
cd nutriscope
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

`pip install -e .` installe les dépendances épinglées de `requirements.txt` **et** le
package `nutriscope` en mode éditable : le code reste dans `src/nutriscope/`, et
`import nutriscope` fonctionne depuis n'importe quel dossier (scripts, tests, notebooks),
sans manipuler `sys.path`.

Vérification :

```bash
python -c "import nutriscope; print(nutriscope.__file__)"
# -> ...\src\nutriscope\__init__.py
```

> Si PowerShell refuse `Activate.ps1`, lancer une fois
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Les données

| Jeu                       | Emplacement                                     | Versionné ? | Rôle                                                      |
| ------------------------- | ----------------------------------------------- | ----------- | --------------------------------------------------------- |
| Échantillon France        | `data-nutriscope/echantillon_france.csv`        | oui         | source par défaut du pipeline et des tests                |
| Jeu ML de la phase 4      | `data-nutriscope/nutriscope_ml_sample.parquet`  | oui         | entrée des notebooks TP 14 et TP 15 (colonne `split` figée) |
| Extrait complet           | `data/en.openfoodfacts.org.products.csv`        | **non**     | mesures de durée (`--full`)                               |
| Sorties du pipeline       | `data/<source>/` (un dossier par source) et `data/logs/` | **non** | régénérables par le pipeline                       |

**Rien n'est à préparer pour l'échantillon** : il est dans le dépôt. Pour l'extrait
complet, télécharger l'export CSV d'Open Food Facts
(<https://world.openfoodfacts.org/data>, fichier `en.openfoodfacts.org.products.csv`,
séparé par des tabulations, environ 13 Go) et le placer dans `data/`.

Variables d'environnement facultatives :

| Variable                       | Effet                                                                 |
| ------------------------------ | --------------------------------------------------------------------- |
| `NUTRISCOPE_SOURCE`            | source brute du pipeline (CSV, TSV ou Parquet), à la place de l'échantillon |
| `NUTRISCOPE_DATA`              | dossier (ou fichier) du jeu ML lu par les notebooks                   |
| `NUTRISCOPE_DB_PASSWORD`       | mot de passe PostgreSQL (sinon lu dans `secrets/db_password.txt`)     |
| `NUTRISCOPE_DB_PASSWORD_FILE`  | autre fichier contenant le mot de passe                               |
| `NUTRISCOPE_DB_USER`, `NUTRISCOPE_DB_HOST`, `NUTRISCOPE_DB_PORT` | connexion (défauts : `postgres`, `localhost`, `5432`) |

Le dossier `secrets/` est ignoré par Git : ne jamais y versionner de mot de passe.

## Lancer le pipeline

Une commande va du CSV brut aux exports prêts pour le ML :

```bash
python -m nutriscope.pipeline all        # ou : make pipeline
```

Avec `make`, les options passent par la variable `ARGS` (`make` refuserait lui-même
une option comme `-a`) : `make pipeline ARGS=--full`,
`make clean-all ARGS=--include-exports`.

Chaque source écrit dans son propre dossier, nommé d'après le fichier source :
`data/echantillon_france/` pour l'échantillon, `data/en-openfoodfacts-org-products/`
pour l'extrait complet (`--name` pour en choisir un autre). Les deux ne s'écrasent
jamais. Le journal des durées, `data/logs/pipeline_runs.jsonl`, est commun.

Les cinq étapes se lancent aussi une par une, dans cet ordre :

```bash
python -m nutriscope.pipeline load            # CSV brut -> data/<source>/raw/
python -m nutriscope.pipeline clean_data      # règles du TP 9 -> data/<source>/clean/
python -m nutriscope.pipeline load_database   # nettoyé -> PostgreSQL (ignorée sans base)
python -m nutriscope.pipeline parquet         # nettoyé -> data/<source>/parquet/ (par rayon)
python -m nutriscope.pipeline exports         # Parquet -> data/<source>/exports/ (split figé)
```

Les noms de l'énoncé (`charger`, `nettoyer`, `charger_base`) sont acceptés. Options
utiles : `--full` (extrait complet), `--source CHEMIN`, `--date AAAAMMJJ` (rejouer une
date), `--force` (réécrire l'export figé du jour), `--require-db` (échouer si la base
manque), `--batches N` (nettoyer en N lots), `--memory 12GB` (plafond mémoire de DuckDB),
`--name NOM` (dossier de sorties). Détail : `python -m nutriscope.pipeline --help` et
[`docs/data/pipeline.md`](docs/data/pipeline.md).

Sur l'extrait complet (13 Go), la source est lue en flux par DuckDB et le nettoyage se
fait automatiquement en 8 lots : comptez une dizaine de Go de mémoire au pic du
chargement, et quelques Go pour le nettoyage. Avec moins de RAM, ajoutez `--memory`
(DuckDB déborde alors sur disque dans `data/<source>/tmp/`) et augmentez `--batches`.

### Sortie attendue

Pour chaque étape, une ligne de statut, le nombre de lignes traitées, la durée et les
fichiers écrits ; la commande se termine par `DONE` (code de retour 0) :

```text
NutriScope pipeline - run date AAAAMMJJ - source data-nutriscope/echantillon_france.csv - outputs data/echantillon_france

[1/5] load
  OK      load: N rows in X.X s
          -> data/echantillon_france/raw/products_raw_AAAAMMJJ.parquet
          -> data/echantillon_france/raw/products_raw_AAAAMMJJ.manifest.json
[2/5] clean_data
  OK      clean_data: N rows in X.X s
...
[3/5] load_database
  SKIPPED load_database: no rows in 0.0 s
          WARNING: database not loaded: no PostgreSQL password configured (...)
...
[5/5] exports
  OK      exports: N rows in X.X s
          split N train / N test, sha256 ...

DONE (X.X s, journal data/logs/pipeline_runs.jsonl)
```

Sans base PostgreSQL, `load_database` est marquée `SKIPPED` avec un avertissement :
c'est normal, le reste du pipeline n'en dépend pas.

Relancé le même jour, `exports` échoue volontairement (`FileExistsError`) : l'export
d'entraînement est figé. Utiliser `--force` pour le réécrire (même empreinte SHA-256
attendue), ou `--date` pour produire un nouvel export daté.

## Vérifier que ça a marché

1. La commande se termine par `DONE`, et `data/echantillon_france/` contient :
   `raw/products_raw_<date>.parquet`, `clean/products_clean_<date>.parquet`,
   `parquet/products_<date>/_SUCCESS`, `exports/features_nutriscore_<date>.parquet` et
   son `.schema.json`.
2. Le split est stratifié : la part de test vaut environ 20 % pour chaque grade.

   ```bash
   python -c "import json, glob; s = json.load(open(sorted(glob.glob('data/echantillon_france/exports/*.schema.json'))[-1], encoding='utf-8')); print(s['split']['counts_by_grade'])"
   ```

3. Les tests passent :

   ```bash
   python -m pytest -q        # ou : make test
   ```

4. `git status` ne montre aucun fichier de données.

## Notebooks

Après `pip install -e .`, choisir le noyau du `.venv` dans Jupyter ou VS Code :

- `notebooks/eda_reference.ipynb` : analyse exploratoire de référence (TP 10) ;
- `notebooks/ml_nutriscore.ipynb` : prédiction du Nutri-Score (TP 14) et méthodes
  d'ensemble (TP 15). Il lit `data-nutriscope/nutriscope_ml_sample.parquet`.

Exécution complète en ligne de commande :

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/ml_nutriscore.ipynb
```

## En cas de panne

| Symptôme                                        | Correction                                                              |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| `ModuleNotFoundError: nutriscope`               | venv non activé, ou `pip install -e .` oublié                           |
| `MissingInputError: ... run the X step first`   | lancer l'étape indiquée, ou `all`                                       |
| `... incomplete (no _SUCCESS marker)`           | relancer `parquet` (exécution précédente interrompue)                   |
| `FileExistsError` sur l'export                  | comportement voulu : `--force` en l'assumant, ou une autre `--date`     |
| `load_database` en `SKIPPED`                    | normal sans base ; sinon définir `NUTRISCOPE_DB_PASSWORD`               |
| `MemoryError` ou poste qui sature (`--full`)    | `--memory 8GB` et `--batches 16`                                        |
| Tout est incohérent                             | `python -m nutriscope.pipeline purge` (ou `make clean`), puis `all`     |
| Faire de la place sur le disque                 | `python -m nutriscope.pipeline purge -a` : toutes les sources           |

`purge` ne supprime que les sorties datées de la source courante (l'échantillon par
défaut, `--full` pour l'extrait complet) et son dossier `tmp/` ; `purge -a` le fait pour
toutes les sources. Jamais les CSV sources, jamais
le journal des durées, et jamais les exports figés (sauf `--include-exports`).

## Structure du dépôt

```text
src/nutriscope/          package Python (pip install -e .)
  pipeline.py            orchestration bout-en-bout (TP 13)
  reader.py, cleaning.py, schema.py, report.py   lecture et nettoyage (TP 9)
  create_database.py     base PostgreSQL (TP 4)
  eda.py, figures.py     analyse exploratoire (TP 10)
  storage/               Parquet partitionné et export figé (TP 12, TP 13)
  classification.py      préparation, plis et métriques de la phase 4 (TP 14, TP 15)
tests/                   tests pytest, sur l'échantillon uniquement
notebooks/               analyses narratives
data-nutriscope/         jeu partagé versionné (échantillon, jeu ML)
data/                    sorties du pipeline (hors Git)
docs/                    cadrage, documentation data et ML
brief/                   énoncés des TP
```
