# NutriScope — pipeline de données (TP 13, jalon J3)

Une commande unique, du CSV Open Food Facts brut aux données prêtes pour le machine learning :

```bash
python -m nutriscope.pipeline all
```

Cinq étapes, lançables seules et rejouables : `charger` → `nettoyer` → `charger_base` → `parquet` → `exports`.
Le schéma du flux, les commandes et les durées mesurées sont dans [`docs/data/pipeline.md`](docs/data/pipeline.md).

Données : © Open Food Facts contributors — [ODbL](https://opendatacommons.org/licenses/odbl/1-0/).

---

## 1. Prérequis

| Élément | Version / remarque |
|---|---|
| Python | **3.12** (vérifier : `py -3.12 --version` sous Windows, `python3.12 --version` ailleurs) |
| Git | pour cloner le dépôt |
| Espace disque | 1 Go pour l'échantillon ; 30 Go libres pour l'extrait complet (fichiers temporaires de tri) |
| PostgreSQL 16 | **seulement** pour l'étape `charger_base` ; sans base, utilisez `--skip charger_base` |

Les données ne sont **pas** dans Git (`data/` est ignoré) : elles sont produites par le pipeline.
Seul l'échantillon de test `data-nutriscope/echantillon_france.csv` (8 689 produits) est versionné :
c'est la source par défaut, rien d'autre à télécharger pour un premier essai.

## 2. Installation

### Windows (PowerShell)

Fermez VS Code pendant l'installation (il peut verrouiller les fichiers d'un environnement virtuel).

```powershell
git clone https://github.com/SebastienHus/Nutriscope_team_delegue.git
cd Nutriscope_team_delegue
git switch tp13-alternative-proposition

py install 3.12                                            # si Python 3.12 manque (voir « py list »)
py -3.12 -m venv $env:USERPROFILE\venvs\nutriscope312     # environnement HORS du dossier du dépôt
$PY = "$env:USERPROFILE\venvs\nutriscope312\Scripts\python.exe"
& $PY -c "import sys; print(sys.version); print(sys.executable)"   # doit afficher 3.12 et ...\venvs\nutriscope312\...
& $PY -m pip install -r requirements-pipeline.txt
```

Dans toute la suite, remplacez `python` par `& $PY`. Les variables PowerShell (`$PY`…) disparaissent quand
on ferme le terminal : redéfinissez-les dans chaque nouvelle fenêtre.

### Linux / macOS

```bash
git clone https://github.com/SebastienHus/Nutriscope_team_delegue.git
cd Nutriscope_team_delegue
git switch tp13-alternative-proposition
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-pipeline.txt
```

## 3. Lancer le pipeline sur l'échantillon (≈ 30 s)

```bash
python -m nutriscope.pipeline all --skip charger_base      # sans PostgreSQL
```

Avec PostgreSQL (serveur démarré, utilisateur capable de créer une base) :

```powershell
$env:DB_PASSWORD = "votre-mot-de-passe"                     # PowerShell ; bash : export DB_PASSWORD=...
python -m nutriscope.pipeline all
```

Sortie attendue (les nombres dépendent de l'échantillon) :

```
--> charger …
[OK  ] charger            1.2 s      8 689 lignes  41 colonnes…
--> nettoyer …
[OK  ] nettoyer           6.0 s      x xxx lignes  8689 -> x xxx lignes, 8 lot(s)
[SAUT] charger_base       0.0 s                    ignorée à la demande (--skip / NUTRISCOPE_SKIP)
--> parquet …
[OK  ] parquet            0.5 s      x xxx lignes  1x partitions (rayons)
--> exports …
[OK  ] exports            0.4 s      x xxx lignes  train x xxx / test xxx
Terminé sans erreur.
```

## 4. Vérifier que ça a marché

```bash
python -m nutriscope.pipeline status        # dernières sorties et durées
python -m pytest -q                          # tous les tests, sur l'échantillon (≈ 1 min)
```

Fichiers produits (dans `data/`, hors Git) :

| Dossier | Contenu |
|---|---|
| `data/raw/` | `produits_bruts_<date>.parquet` + manifeste (empreinte de la source) |
| `data/clean/` | `produits_propres_<date>.parquet`, `rapport_nettoyage_<date>.md`, `regles_<date>.json` |
| `data/db/` | `base_<date>.json` (lignes par table chargée) |
| `data/parquet/` | `produits_<date>/` partitionné par rayon, `schema_products.json`, `_SUCCESS` |
| `data/exports/` | **`features_nutriscore_<date>.parquet`** (colonne `split`) + `.schema.json` |
| `data/logs/` | `pipeline_journal.jsonl` : une ligne par étape (durée, statut, lignes) |

## 5. Commandes utiles

| Besoin | Commande |
|---|---|
| Tout le pipeline | `python -m nutriscope.pipeline all` |
| Une étape seule | `python -m nutriscope.pipeline nettoyer` (elle retrouve la dernière entrée datée) |
| Sans PostgreSQL | `... all --skip charger_base` |
| Fichier complet OFF (12 Go) | `... all --source data/en.openfoodfacts.org.products.csv` (séparateur détecté) |
| Rejouer une date | `... exports --date 20261014 --force` |
| Nettoyage en un seul bloc | `... nettoyer --batches 1` (14 Go de RAM sur le fichier complet) |
| Tout effacer et relancer | `python -m nutriscope.pipeline clean` puis `... all` |
| Avec make (Linux/macOS) | `make pipeline`, `make pipeline-sans-base`, `make test` |

Toutes les options ont une variable d'environnement équivalente (`NUTRISCOPE_SOURCE`, `NUTRISCOPE_DATE`,
`NUTRISCOPE_BATCHES`, `DB_HOST`, `DB_PASSWORD`…) : voir `.env.example` et `nutriscope/config.py`.

## 6. Dépannage

| Symptôme | Cause | Correction |
|---|---|---|
| `No module named nutriscope` | lancé hors de la racine du dépôt | `cd` à la racine, puis `python -m nutriscope.pipeline …` |
| `Defaulting to user installation` / chemin `Python38` | ce n'est pas le Python du venv | utiliser `& $PY` (Windows) ou activer `.venv` |
| `WinError 32` pendant `pip install` | un éditeur verrouille le venv | fermer VS Code, venv hors du dépôt |
| `Mot de passe PostgreSQL absent` | `DB_PASSWORD` non défini | le définir, ou `--skip charger_base` |
| `Aucun … trouvé : lancez d'abord …` | étape lancée sans son entrée | lancer l'étape indiquée |
| `export du jour déjà figé` | comportement voulu (export figé) | autre `--date`, ou `--force` en l'assumant |
| Mémoire saturée sur le fichier complet | plafond trop haut pour la machine | `--memory 8GB`, garder `--batches 8` |

## 7. Documentation

- [`docs/data/pipeline.md`](docs/data/pipeline.md) — flux, commandes, durées, ce que la phase 4 lira.
- [`docs/tp13/JOURNAL_ACTIONS.md`](docs/tp13/JOURNAL_ACTIONS.md) — tout ce qui a été fait sur cette branche et pourquoi.
- [`docs/journal_tp13.md`](docs/journal_tp13.md) — journal de l'équipe pour le TP 13.
- [`docs/tp13/audit/`](docs/tp13/audit/) — audit du projet (problèmes P-01 à P-36), plan, conception.
- [`docs/tp13/banc_essai/JOURNAL_DEMARCHE.md`](docs/tp13/banc_essai/JOURNAL_DEMARCHE.md) — mesures sur le fichier complet.
- [`docs/tp13/conteneurisation/`](docs/tp13/conteneurisation/) — préparation (non activée) d'un conteneur.
