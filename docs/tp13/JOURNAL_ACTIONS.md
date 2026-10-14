# Journal des actions — branche `tp13-alternative-proposition`

> Ce document trace **tout ce qui a été fait** sur cette branche, **pourquoi**, et **à quel point de l'audit ou de
> l'énoncé du TP 13 chaque action répond**. Il complète le journal d'équipe (`docs/journal_tp13.md`).
> Références : audit `docs/tp13/audit/03_problemes_identifies.md` (P-01 à P-36), mesures
> `docs/tp13/banc_essai/JOURNAL_DEMARCHE.md`, énoncé `brief/` du TP 13.
>
> Données : © Open Food Facts contributors — ODbL.

## 1. Règles de travail fixées par l'équipe (14/10/2026)

| Règle | Conséquence |
|---|---|
| Nouvelle branche depuis `develop`, nommée `tp13-alternative-proposition` | `develop` n'est pas touchée |
| **Aucun commit** fait par l'assistant | l'équipe relit `git status` / `git diff` et committe elle-même |
| **`src/` (TP 9, TP 12) n'est pas modifié** : « on repart sur du propre » | tout le TP 13 vit dans le nouveau package `nutriscope/`, qui **importe** le code existant ; chaque correction est faite dans `nutriscope/` et tracée ici |
| Nettoyage en **8 lots** par défaut | réglable : `--batches 1` ou `NUTRISCOPE_BATCHES=1` |
| Pas de conteneur pour le J3, mais tout doit y être adaptable | configuration par variables d'environnement ; brouillons dans `docs/tp13/conteneurisation/` |
| Tous les pays | aucun filtre géographique dans le pipeline |

**Limite importante** : l'assistant a écrit le code et les tests **sans pouvoir les exécuter** (pas d'accès à
Python avec pandas/DuckDB sur la machine de l'équipe). Seules la syntaxe et les parties sans dépendances
(configuration, recherche des entrées datées, CLI `--help`/`status`, fusion des comptes rendus, texte SQL du
split) ont été vérifiées. **Le premier `pytest` est fait par l'équipe** (section 6).

## 2. Chronologie

| # | Action | Détail |
|---|---|---|
| A-01 | Audit du dépôt et des branches | état de `develop`, 9 branches lues, énoncés TP 9/10/12/13, guide `TP13_Guide_Comprehension` → `docs/tp13/audit/` (36 problèmes) |
| A-02 | Banc d'essai hors dépôt sur le fichier complet | 12,1 Go, 4 535 553 lignes : chargement DuckDB 23 s (0 perte) ; nettoyage TP 9 en 8 lots 2,5 Go → 996 637 lignes ; doublons 60/50 expliqués → `docs/tp13/banc_essai/` |
| A-03 | Création de la branche | `git switch -c tp13-alternative-proposition` depuis `develop` au commit `0fd7514` (arbre propre, aucun fichier modifié avant) |
| A-04 | Package `nutriscope/` (orchestration) | `__init__.py`, `__main__.py`, `config.py`, `legacy.py`, `files.py`, `duck.py`, `journal.py`, `reporting.py`, `pipeline.py` |
| A-05 | Les cinq étapes | `nutriscope/steps/` : `base.py`, `charger.py`, `nettoyer.py`, `charger_base.py`, `parquet.py`, `exports.py` |
| A-06 | Façade Makefile | `Makefile` : appelle uniquement la CLI |
| A-07 | Tests | `tests/test_pipeline_tp13.py` : 20 tests sur l'échantillon, dossiers temporaires |
| A-08 | Dépendances et configuration | `requirements-pipeline.txt` (nouveau, épinglé sur les versions mesurées), `.env.example` |
| A-09 | README réécrit | installation Windows/Linux, commandes, sortie attendue, vérification, dépannage |
| A-10 | Documentation | `docs/data/pipeline.md`, `docs/journal_tp13.md`, `docs/tp13/` (audit, banc d'essai, conteneurisation, ce journal) |

## 3. Corrections et réponses aux problèmes de l'audit

Aucune de ces corrections ne modifie `src/` : elles sont faites dans `nutriscope/`, autour du code existant.

| Problème (audit) | Pourquoi c'était un problème | Ce qui a été fait | Où | Répond à |
|---|---|---|---|---|
| **P-13** mémoire saturée sur le fichier complet | pandas lit tout puis `pd.concat` ; le nettoyage copie plusieurs fois | lecture **DuckDB** en flux (41 colonnes, texte, plafond mémoire, débordement disque) ; nettoyage **par lots** `hash(trim(code)) % N` | `steps/charger.py`, `steps/nettoyer.py` | TP 13 « lire par DuckDB » ; mesures A-02 |
| **P-35** marge mémoire faible en un bloc (4,9 Go libres) | échec probable sur une machine de 16 Go (test machine vierge) | **8 lots par défaut** (2,5 Go de pic mesuré) | `config.py` | TP 13 §4 |
| **P-07** `convert_parquet` sans `ORDER BY`, multi-thread, sans `_SUCCESS`, non daté, `rmtree` sans garde-fou | deux exécutions ≠ mêmes octets ; dossier à moitié écrit lisible ; risque d'effacer `data/` | étape `parquet` réécrite autour des fonctions du TP 12 (`column_type`, `partition_expression`) : `ORDER BY code`, 1 thread, écriture dans `.tmp`, `_SUCCESS` en dernier, renommage, dossier daté, suppression seulement dans `data/` | `steps/parquet.py`, `files.py` | TP 13 §2 (idempotence, `_SUCCESS`, dates), PC 2 |
| **P-09** mot de passe par `getpass` / `-pwd` | bloque une commande unique et un conteneur ; mot de passe dans l'historique | `DB_PASSWORD` (environnement) ; saisie seulement si terminal ; sinon échec clair ; mot de passe jamais écrit | `steps/charger_base.py`, `config.py` | TP 13 §1 (commande unique) |
| **P-08** chemins relatifs au dossier courant | ne marche que lancé depuis la racine | chemins calculés depuis `nutriscope/config.py` (`ROOT`) + variables d'environnement | `config.py` | TP 13 §1.4 |
| **P-06** imports « à plat », `src/pipeline.py` homonyme | `ModuleNotFoundError` selon le dossier ; confusion des deux `pipeline` | `legacy.py` ajoute `src/` une fois ; on appelle toujours `nutriscope.pipeline` | `legacy.py` | TP 13 §1.2 (« importez-la ») |
| **P-10** nettoyé en CSV | perte des types (entiers nullables, dates, booléens) | nettoyé en **Parquet** | `steps/nettoyer.py` | cohérence base / Parquet |
| Rapport du TP 9 (`report.generate_report`) | a besoin du brut complet en mémoire et écrit l'heure dans le rapport | rapport construit en additionnant les comptes rendus des lots, heure dans le manifeste | `reporting.py` | lots + idempotence |
| **TP 13 §3** split train/test | absent | colonne `split`, stratifiée par grade, graine 42, 20 % ; rang `md5('42:' || code)` ; effectifs par grade, méthode, graine et règles d'usage dans le schéma | `steps/exports.py` | TP 13 §3, PC 3 |
| **P-16** `FileExistsError` dans `all` | un 2ᵉ `all` le même jour planterait | dans `all` l'export existant est **sauté** (statut `skipped`) ; `--force` pour réécrire | `steps/exports.py` | TP 13 §3.3 (export figé) |
| **P-14** date en UTC dans un conteneur | fichiers datés de la veille entre 0 h et 2 h | date en fuseau Europe/Paris ; `NUTRISCOPE_DATE` / `--date` pour rejouer | `config.py` | TP 13 §2.1 |
| **P-15** commit Git absent dans un conteneur | schéma « unknown » | `NUTRISCOPE_GIT_COMMIT` prioritaire, sinon `git` (fonction du TP 12) | `steps/exports.py` | traçabilité phase 4 |
| **P-12** chargement base non testé | aucune vérification automatique | test de `prepare_tables` sans base ; test réel optionnel (`NUTRISCOPE_TEST_DB=1`) ; contrôle produits = nettoyé dans l'étape | `tests/`, `steps/charger_base.py` | TP 13 §6 |
| Journal des durées (TP 13 §2.5) | absent | `data/logs/pipeline_journal.jsonl`, une ligne par étape, **échecs et sauts compris** | `journal.py`, `steps/base.py` | TP 13 §2.5, §5 |
| Entrée introuvable (TP 13 §2.2) | trace Python brute | chaque étape cherche sa sortie du jour puis la plus récente, ignore un dossier sans `_SUCCESS`, sinon « lancez d'abord … » | `files.find_input` | TP 13 §2.2 |
| **P-01 / P-36** dépendances non épinglées | autres versions = autres octets | `requirements-pipeline.txt` épinglé sur les versions du banc d'essai ; versions recopiées dans chaque manifeste ; `requirements.txt` existant **non modifié** (notebooks) | racine | TP 13 §6.2 |
| **P-03** `psycopg` sans binaire | `libpq` absente → erreur d'import | `psycopg[binary]` | `requirements-pipeline.txt` | machine vierge |
| **P-04** `zoneinfo` sans `tzdata` | erreur sous Windows / image minimale | `tzdata` ajouté ; repli sur la date locale si absent | `requirements-pipeline.txt`, `config.py` | machine vierge |
| **P-05** Windows : `make`, encodage, CRLF | `make` absent ; `UnicodeEncodeError` ; scripts CRLF | CLI d'abord (Makefile = façade) ; sortie forcée en UTF-8 ; `PYTHONUTF8=1` dans le Makefile ; CRLF : `.gitattributes` **proposé seulement** (non activé) | `pipeline.py`, `Makefile`, `docs/tp13/conteneurisation/` | TP 13 §4 |
| **P-29** venv verrouillé par VS Code | `WinError 32`, mauvais Python | méthode validée dans le README (venv hors dépôt, `& $PY`) | `README.md` | TP 13 §4 |
| **P-30** décision « tous les pays » | contredit `perimetre.md` | documentée dans `pipeline.md` et le journal ; `perimetre.md` **non modifié** (à faire par l'équipe) | `docs/` | phase 4 |
| **D-1** guide : `train.parquet`/`test.parquet` | contredit l'énoncé | colonne `split` dans l'export (énoncé) | `steps/exports.py` | TP 13 §3.1 |
| **P-17** branche `feature/docker-compose` | autre projet (stack LLM) | **non fusionnée** ; seules des idées reprises (healthcheck, `.env.example`) | — | — |

## 4. Fichiers touchés

**Créés** : `nutriscope/` (16 fichiers), `tests/test_pipeline_tp13.py`, `Makefile`, `requirements-pipeline.txt`,
`.env.example`, `docs/data/pipeline.md`, `docs/journal_tp13.md`, `docs/tp13/` (ce journal, `audit/`,
`banc_essai/`, `conteneurisation/`).

**Modifié** : `README.md` (réécrit : il ne contenait qu'une ligne).

**Non modifiés** : tout `src/`, `tests/test_cleaning.py`, `tests/test_eda.py`, `tests/test_storage.py`,
`tests/conftest.py`, `requirements.txt`, `.gitignore` (`/data/` déjà ignoré), `docs/journal.md`, `docs/architecture.md`,
`docs/cadrage/`. Aucun fichier de données ajouté.

Vérification : `git status` doit montrer `README.md` modifié et uniquement des fichiers nouveaux.

## 5. Choix de conception (et alternatives écartées)

| Choix | Pourquoi | Alternative écartée |
|---|---|---|
| CLI Python + Makefile façade | Windows sans `make` ; une seule logique | Makefile seul ; Airflow/Prefect (flux de quelques minutes : inutile) |
| Lots par `hash(trim(code))` | un même code toujours dans le même lot → déduplication juste | lots par tranches de lignes (doublons séparés) |
| Split par rang `md5(graine:code)` dans chaque grade | exactement 20 % par grade ; stable produit par produit ; indépendant des versions | `train_test_split` de scikit-learn (dépend de l'ordre et de la version) |
| Export TP 12 réutilisé (`features_query`, `FEATURES`, `FILTERS`) + colonne `split` | ne pas refaire le TP 12 | réécrire les filtres |
| Parquet `data/parquet/produits_<date>/produits/…` | daté, `_SUCCESS` et schéma à côté des données | dossier unique écrasé à chaque fois (TP 12) |
| Écriture `.tmp` puis renommage | jamais de sortie à moitié écrite | écriture directe |

## 6. Validation à faire par l'équipe (dans cet ordre)

```powershell
cd C:\Users\Administrateur\Desktop\cours\exo\Nutriscope_team_delegue
git status                                   # README.md modifié + fichiers nouveaux seulement
$PY = "$env:USERPROFILE\venvs\nutriscope312\Scripts\python.exe"    # ou un venv neuf (README §2)
& $PY -m pip install -r requirements-pipeline.txt
& $PY -m pytest -q tests/test_pipeline_tp13.py                    # 1) tests du TP 13
& $PY -m pytest -q                                                 # 2) tous les tests (TP 9, 10, 12, 13)
& $PY -m nutriscope.pipeline all --skip charger_base               # 3) commande unique sur l'échantillon
& $PY -m nutriscope.pipeline parquet ; & $PY -m nutriscope.pipeline parquet   # 4) PC 2 : relance sans changement
& $PY -m nutriscope.pipeline status                                # 5) durées du journal → docs/data/pipeline.md
$env:DB_PASSWORD = "..." ; & $PY -m nutriscope.pipeline charger_base         # 6) avec PostgreSQL
& $PY -m nutriscope.pipeline all --source data\en.openfoodfacts.org.products.csv   # 7) extrait complet (≈ 5 min)
```

Coller les sorties en cas d'échec : chaque correction sera ajoutée ici (section 8).

Zones de risque connues (code non exécuté par l'assistant) : syntaxe DuckDB du `COPY … PARTITION_BY` avec `ORDER BY`
et de `hive_types` ; fenêtre SQL du split ; types après `pd.concat` des lots puis `to_parquet` ; tests
`test_tables_de_la_base_sans_postgresql` (dépend de `sqlalchemy`, `sqlparse`, `sqlalchemy-utils`) ; tests existants
du TP 9/12 avec les versions plus récentes de pandera/numpy.

## 7. Ce qui reste à faire (hors de cette branche ou après validation)

- [ ] Premier `pytest` et corrections éventuelles (section 8).
- [ ] Remplir le tableau des durées de `docs/data/pipeline.md` à partir du journal (échantillon **et** extrait complet).
- [ ] Mettre à jour `docs/cadrage/parties/perimetre.md` : décision « tous les pays » (P-30).
- [ ] Figer l'environnement : `pip freeze > requirements-lock.txt` après un `pytest` vert (P-01).
- [ ] Test machine vierge par une autre équipe ; corrections committées avec un message qui dit ce qui manquait.
- [ ] Examiner les 446 494 lignes écartées par `filter_codes` (P-31) et l'écart France vs TP 2 (P-33).
- [ ] Décider de `.gitattributes` (P-05, proposé dans `docs/tp13/conteneurisation/`).
- [ ] Commits (par l'équipe), PR vers `develop`, tag annoté `v0.3`.

## 8. Corrections après les premiers essais

Format : identifiant, date, symptôme (ou motif), cause, correction, fichier.

| # | Date | Symptôme / motif | Cause | Correction | Fichier |
|---|---|---|---|---|---|
| C-00 | 14/10 | relecture avant tout essai | `create_database` importe `sqlalchemy_utils` au chargement ; sans ce paquet, le test « base sans PostgreSQL » échouait au lieu d'être sauté | ajout de `pytest.importorskip("sqlalchemy_utils")` | `tests/test_pipeline_tp13.py` |
