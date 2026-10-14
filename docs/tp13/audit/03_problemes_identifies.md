# Problèmes identifiés (et à anticiper) — toutes branches

Légende : **Constaté** = vu dans les fichiers/l'historique Git. **Probable** = déduit du code, *à vérifier* en l'exécutant. **Anticipé** = surviendra avec le TP 13 / Docker.
Gravité : 🔴 bloque le livrable · 🟠 peut casser chez l'autre équipe · 🟡 confort / propreté.
Méthode : lecture de `develop` (état au 14/10), des branches `origin/*`, des énoncés TP 9/10/12/13 et du guide. Code **non exécuté** (installation des dépendances bloquée dans mon environnement).

## A. Environnement et dépendances

| ID | Constat | Gravité | Pourquoi c'est un problème | Correctif |
|---|---|---|---|---|
| P-01 | `requirements.txt` sans aucune version, et mélange pipeline + exploration (`umap-learn`, `seaborn`, `nbconvert`, `matplotlib`, `scikit-learn`). *Constaté* | 🔴 | L'énoncé demande « épinglé ». Sans versions, l'autre équipe installe d'autres versions → comportement et **octets** différents. `umap-learn` tire `numba`, lourd et souvent en retard sur les nouvelles versions de Python. | Séparer `requirements-pipeline.txt` (pandas, numpy, pyarrow, duckdb, pandera, sqlalchemy, sqlalchemy-utils, sqlparse, `psycopg[binary]`, tzdata) et `requirements-dev.txt` (pytest, nbconvert, matplotlib, seaborn, scikit-learn, umap-learn). Épingler avec `pip freeze` **depuis un venv 3.12 neuf où les tests passent**. |
| P-02 | `.venv` créé avec **Python 3.14**, `CONTRIBUTING.md` dit **3.12**. *Constaté* | 🔴 | Roues binaires (pyarrow, duckdb, numba) parfois absentes pour la toute dernière version de Python ; résultats non reproductibles entre membres. | Choisir 3.12 partout (Dockerfile, README, `.python-version` facultatif). Recréer le venv. |
| P-03 | `psycopg` (sans `[binary]`) dans les dépendances. *Constaté* | 🟠 | Sans extra binaire, `psycopg` exige la bibliothèque système `libpq` : absente d'une image `python:slim` et de beaucoup de postes → `ImportError: no pq wrapper available`. | `psycopg[binary]`. |
| P-04 | `zoneinfo` (fuseau Europe/Paris pour dater les sorties) a besoin du paquet `tzdata` sous Windows et dans les images minimales. *Anticipé* | 🟠 | Sinon `ZoneInfoNotFoundError`. | Ajouter `tzdata` aux dépendances. |
| P-05 | Équipe sous **Windows** : (a) `make` n'est pas installé par défaut ; (b) `src/pipeline.py` affiche `✓ ✗ ○ ✅` → `UnicodeEncodeError` quand la sortie est redirigée (console cp1252) ; (c) aucun `.gitattributes` et `core.autocrlf` non défini : `src/create_database.py` est déjà en fins de ligne **CRLF** alors que les autres fichiers sont en LF. *Constaté* | 🟠 | (a) `make pipeline` ne marchera pas chez tous → la **CLI Python est la vraie interface**, le Makefile une façade (ça rejoint l'énoncé). (b) casse sous Makefile/`tee`/Docker mal configuré. (c) un `Makefile`, `Dockerfile` ou script `.sh` en CRLF échoue (`missing separator`, `\r: command not found`) dès que Docker/Linux le lit. | (a) CLI d'abord. (b) `PYTHONUTF8=1` (Makefile + Dockerfile) et/ou `sys.stdout.reconfigure(encoding="utf-8")`. (c) ajouter `propose/.gitattributes`, puis `git add --renormalize .`. |

## B. Code existant

| ID | Constat | Gravité | Pourquoi | Correctif |
|---|---|---|---|---|
| P-06 | Imports « à plat » (`import cleaning`, `from storage...`) via `sys.path.insert` répétés dans `convert_parquet.py`, `export_features.py` et `tests/conftest.py`. Aucun `pyproject.toml`/`setup.py`. Et `src/pipeline.py` (TP 9) existe déjà. *Constaté* | 🟠 | `ModuleNotFoundError` selon le dossier de lancement ; `import pipeline` désignera le **TP 9** quand `src/` est dans le chemin → confusion avec `nutriscope.pipeline`. | Module `nutriscope/_legacy.py` qui ajoute `src/` une seule fois, chemin calculé depuis `__file__`. Toujours `python -m nutriscope.pipeline`. Dette notée : renommer/déplacer plus tard. |
| P-07 | `convert_parquet.py` : (a) `SELECT … FROM relation` **sans `ORDER BY`** et DuckDB multi-thread → l'ordre des lignes dans les fichiers peut varier d'une exécution à l'autre ; (b) pas de `_SUCCESS` ; (c) sortie non datée (`data/parquet/products`) ; (d) `shutil.rmtree(destination)` sur un chemin passé en argument, sans garde-fou ; (e) si le script plante après `rmtree`, il reste un dossier partiel lisible. *Constaté (a-e) / à vérifier (a: effet réel)* | 🔴 | C'est exactement le PC 2 : « relancer `parquet` deux fois : empreintes identiques ». (d) `destination=data` effacerait tout `data/`. | `ORDER BY "code"` + `SET threads = 1` (comme déjà fait dans `export_features.py`) ; écrire dans `<dossier>.tmp`, `_SUCCESS`, puis `os.replace` ; refuser de supprimer un dossier qui n'est ni vide ni un ancien jeu Parquet (présence de `schema_products.json`/`_SUCCESS`). |
| P-08 | Chemins relatifs au **dossier courant** : `src/pipeline.py` met `csv_in="./data-nutriscope/echantillon_france.csv"` et `report_path="./data/docs/rapport_nettoyage.md"` par défaut ; `convert_parquet.DEFAULT_SOURCE` = `data/clean/en.openfoodfacts.org.products.csv` (nom du **gros** fichier). *Constaté* | 🟠 | Lancé depuis un autre dossier ou avec l'échantillon, ça échoue ; l'énoncé l'interdit (« résoudre par rapport au fichier »). | Tout passe par `nutriscope/config.py` (chemins depuis `__file__` + variables d'environnement). |
| P-09 | `create_database.py` / `src/pipeline.py` : mot de passe saisi avec `getpass` ou `-pwd` en ligne de commande ; un `TODO: Besoin du container Postgresql et des secrets`. Hôte/port passés seulement en options CLI. *Constaté* | 🔴 | `getpass` **bloque** dans Docker/CI (pas de terminal) ; `-pwd` reste dans l'historique du shell. Une commande unique ne peut pas s'arrêter pour demander un mot de passe. | Lire `DB_PASSWORD` (et `DB_HOST`, `DB_PORT`, `DB_USER`) dans l'environnement ; `getpass` seulement en dernier recours si un terminal est présent. `.env` ignoré par Git, `.env.example` versionné. |
| P-10 | Le « nettoyé » est écrit en **CSV** (`df_clean.to_csv`). `convert_parquet` relit ce CSV en `all_varchar` puis re-caste. *Constaté* | 🟡→🟠 | Types perdus (`Int64`, timestamps, booléens) ; `load_products` attend un DataFrame **tel que sorti de `clean()`**, donc recharger le CSV peut changer les comptages ou les types. | Écrire le nettoyé en Parquet, ou documenter et tester le comptage base = Parquet (PC 1). `to_parquet` accepte déjà un `.parquet` en source. |
| P-11 | Le SHA-256 d'un Parquet dépend de la **version** de DuckDB/pyarrow (métadonnées `created_by`, encodage). *Probable, à vérifier* | 🟠 | « Même empreinte » n'est vrai qu'à versions égales ; deux machines à versions différentes → empreintes différentes **sans que les données aient changé**. | Versions épinglées (P-01) ; indiquer dans `schema.json` les versions de duckdb/pyarrow ; comparer aussi les **contenus** (lignes triées) dans les tests si besoin. |
| P-12 | Aucun test pour `create_database.py` ; son DDL fait `DROP TABLE … CASCADE` sur la base configurée. *Constaté* | 🟠 | `charger_base` ne sera jamais vérifiée automatiquement ; un mauvais nom de base (ou une base partagée) perd des données. | Tester `prepare_tables` (fonction pure, sans PostgreSQL) ; un test `skipif` pour la vraie base ; la base du pipeline est **dédiée** (`nutriscope`, conteneur à part). |
| P-13 | Données : seul l'**échantillon** (8 689 lignes) est dans le dépôt. L'« extrait France » du jeu partagé n'y est pas ; `data/produits_fr.csv` (298 Mo, 8 colonnes) n'est **pas** l'extrait attendu (colonnes différentes). Le CSV complet fait 13 Go, et les commandes de `05-commandes-reelles.md` utilisent `--chunksize 1000`. *Constaté* | 🟠 | Le tableau des durées exige « échantillon **et** extrait » ; `chunksize 1000` suggère que la mémoire a posé problème ; `pd.concat` + nettoyage pandas de millions de lignes peut saturer. | Demander/copier l'extrait du jeu partagé (`supports/data-nutriscope/`) ; sinon dire explicitement dans pipeline.md quel fichier a servi aux mesures. Prévoir un plan B DuckDB (lire seulement les colonnes utiles) si la RAM sature. **[MAJ 14/10] Résolu par mesure** : le fichier fait 211 colonnes et 4 535 553 lignes ; chargement DuckDB 23 s, nettoyage en 8 lots 2,5 Go de pic (banc d'essai). |

## C. Dates, reproductibilité, fichiers figés

| ID | Constat | Gravité | Pourquoi | Correctif |
|---|---|---|---|---|
| P-14 | `export_features` utilise `date.today()` ; dans un conteneur l'heure est **UTC**. *Anticipé* | 🟠 | Entre 00:00 et 02:00 (heure de Paris), le conteneur est encore « hier » → fichiers datés différemment selon la machine, tests flous autour de minuit. | Variable `NUTRISCOPE_DATE`, sinon date calculée en `Europe/Paris` (+ `TZ` dans Docker, + `tzdata`). Une seule date par exécution, passée à toutes les étapes. |
| P-15 | `git_commit()` appelle `git` ; dans l'image Docker il n'y a ni `git` ni `.git`. Il ajoute aussi `-dirty` si l'arbre est modifié. *Constaté / anticipé* | 🟡 | `schema.json` dira `unknown`, ou `…-dirty` si tu exportes avant de committer → traçabilité douteuse. | Lire d'abord `NUTRISCOPE_GIT_COMMIT` (passé en `--build-arg`), et exporter **après** commit pour le gel officiel. |
| P-16 | `export_features` lève `FileExistsError` si l'export du jour existe. *Constaté* | 🟠 | Dans `all`, une 2ᵉ exécution le même jour planterait alors que c'est le comportement attendu (figé). | Dans `all` : statut `skipped (déjà figé)`, pas d'échec ; réécriture seulement avec `--force`. Pour la phase 4 : nouvelle date = nouvel export. |

## D. Divergences guide ↔ énoncé (l'énoncé fait foi)

| ID | Guide `TP13_Guide_Comprehension` | Énoncé | Décision proposée |
|---|---|---|---|
| D-1 | `split.py` produisant `train.parquet` / `test.parquet` | une colonne `split` **dans** `features_<date>.parquet` | Suivre l'énoncé. Si tu veux les deux fichiers, les **dériver** de la colonne (cible `make splits`), jamais l'inverse. |
| D-2 | Flux « pipeline.py → convert → export → split » | 5 étapes **nommées** : `charger`, `nettoyer`, `charger_base`, `parquet`, `exports` | Utiliser ces noms exacts dans la CLI. |
| D-3 | Docker en phase 6 | non exigé | Votre équipe le veut : faites-le **après** PC 2, et gardez le chemin `venv` dans le README (le poste d'en face n'a peut-être pas Docker). |
| D-4 | Checklist : `train.parquet`, `test.parquet` | `schema.json`, colonne `split`, journal des durées | Cocher d'abord la grille de l'énoncé (20 pts). |

## E. Git et branches

| ID | Constat | Gravité | Correctif |
|---|---|---|---|
| P-17 | `origin/feature/docker-compose` est le **corrigé d'un autre TP Docker** (stack web + API FastAPI + PostgreSQL + LLM llama.cpp + Prometheus/Grafana/Loki), avec son propre `README.md`, `CONTRIBUTING.md`, `.gitignore`, `docs/architecture.md`, `brief/`. 44 fichiers. *Constaté* | 🟠 | **Ne pas la fusionner** : conflits garantis sur README/architecture/.gitignore et fichiers hors sujet. On s'en inspire seulement (healthcheck, `.env.example`, utilisateur non-root). Le schéma `db/init/001_schema.sql` y est celui de `llmapp`, pas de NutriScope. |
| P-18 | L'énoncé suggère `git add -A && git commit …`. `.gitignore` couvre `/data/` mais pas toujours les fichiers générés (`work`, `tree.txt`, futurs `.env`, `*.tmp`). *Constaté* | 🟡 | `git status` puis `git add` ciblé ; relire `git diff --staged --stat` avant de committer. `.env` est déjà ignoré, ajouter `*.tmp` et `data/` reste ignoré. |
| P-19 | `feature/tp13-regression` (local et distante) existe déjà, mais ne contient que le déplacement du brief ; son nom parle de **régression** (phase ML), pas de pipeline. *Constaté* | 🟡 | Décider en équipe : renommer ou ouvrir `feature/tp13-pipeline`. Éviter deux branches pour le même TP. |
| P-20 | Seul le tag `v0.1.0` existe (sur `main`, 9 sept.) ; `main` est très en retard sur `develop` (82 fichiers). `CONTRIBUTING.md` interdit les commits directs sur `main`. *Constaté* | 🟠 | Définir où va `v0.3` : sur le commit de fusion dans `develop` **ou** sur `main` après PR. Poser un tag **annoté** (`git tag -a`) et vérifier `git tag -n`. Sauter `v0.2` est possible mais à noter dans le journal. |
| P-21 | L'échantillon (4,7 Mo) est suivi par Git (`data-nutriscope/`), alors que le gros CSV est ignoré ; `docs/data/` (versionné) cohabite avec `data/` (ignoré) : noms proches. *Constaté* | 🟡 | Voulu et utile (tests + machine vierge) — l'écrire dans le README pour éviter la confusion « données hors Git ». |

## F. Conteneur (Docker) — à anticiper

| ID | Risque | Gravité | Parade |
|---|---|---|---|
| P-22 | Port 5432 déjà pris par un PostgreSQL local (vous utilisez l'utilisateur `postgres` en local). | 🟠 | Ne pas publier le port du conteneur `db` (le pipeline y accède par le réseau Compose), ou le publier en `5433`. |
| P-23 | `DB_HOST=localhost` dans un conteneur désigne le conteneur lui-même, pas la base ; la base démarre plus lentement que le pipeline. | 🔴 | `DB_HOST=db` (nom du service) ; `healthcheck` sur `db` + `depends_on: condition: service_healthy`. |
| P-24 | Sous Windows, les dossiers montés (`bind mount`) sont lents ; WSL2 limite la RAM par défaut ; le CSV de 13 Go ne doit jamais être copié dans l'image. | 🟠 | Image sans données (`.dockerignore`), `./data` en volume, échantillon dans l'image pour le test vierge ; extrait complet monté en lecture seule. |
| P-25 | Sous Linux, fichiers créés dans un volume par le conteneur appartiennent à `root`. | 🟡 | Utilisateur non-root dans l'image (`USER`) / `user: "${UID}:${GID}"`. |
| P-26 | Mot de passe PostgreSQL écrit en clair dans `compose.yml` ou dans l'image. | 🔴 | `.env` (ignoré) + `.env.example` ; jamais de secret dans le Dockerfile (`docker history` le montre). |
| P-27 | L'autre équipe n'a pas Docker (postes de formation sans droits). | 🟠 | Le README décrit les **deux** voies : `venv` + PostgreSQL local, et Docker. L'étape `charger_base` peut être sautée explicitement (`--skip charger_base`) **et journalisée** si aucune base n'est joignable. |
| P-28 | Image lourde / build lent (dépendances d'exploration, `COPY .`). | 🟡 | `requirements-pipeline.txt` seul, copié **avant** le code (cache des couches), `.dockerignore`. |

## Les 5 à traiter en premier

1. **P-09** mot de passe non interactif (sinon pas de commande unique).
2. **P-07** déterminisme du Parquet (sinon PC 2 échoue).
3. **P-01 / P-02** versions épinglées et Python 3.12 (sinon pas de machine vierge).
4. **P-23** `DB_HOST=db` + healthcheck (sinon Docker échoue au premier lancement).
5. **P-14** date unique en fuseau Paris (sinon noms de fichiers incohérents).

## G. [MAJ 14/10] Constats du banc d'essai « gros fichier »

| ID | Constat | Gravité | Correctif / suite |
|---|---|---|---|
| P-29 | Windows : un venv dans le dossier du projet est verrouillé par VS Code (`WinError 32`, `python.exe` accès refusé), et `python` sans venv activé désigne le Python 3.8 du système. *Constaté* | 🟠 | venv hors du projet (`%USERPROFILE%\venvs\…`), VS Code fermé pendant l'installation, appeler `& $PY` et vérifier `sys.executable`. À écrire dans le README. |
| P-30 | **Décision : tous les pays** (pas de filtre géographique). Le document `docs/cadrage/parties/perimetre.md` dit encore « commercialisé en France ». *Constaté* | 🟠 | Mettre à jour le document de périmètre et `docs/journal_tp13.md` ; le dire dans `pipeline.md` (la phase 4 doit le savoir). |
| P-31 | `filter_codes` écarte **446 494 lignes (9,8 %)** sur le fichier complet. *Constaté* | 🟡 | Vérifier quels codes sont rejetés (longueur, chiffre répété, préfixe 200-299) avant de citer le chiffre. |
| P-32 | 60 lignes en double dans le brut, 50 supprimées par `deduplicate_codes`. *Constaté* | ✅ | **Résolu (script 05)** : 10 codes en double ne sont pas officiels (4 préfixes magasin 200-299, 6 codes de 14/15/18 chiffres) et sont écartés par `filter_codes` avant la déduplication. Aucun doublon n'est une copie exacte. |
| P-33 | 1 263 854 produits France dans le fichier contre ≈ 1 136 108 au profilage TP 2. *Constaté* | 🟡 | Hypothèses : export plus récent, colonne `countries` vs `countries_tags`. Sans impact (tous les pays), à expliquer si cité. |
| P-34 | Les 500 premiers Mo et le premier million de lignes ne sont pas représentatifs (fichier trié par code : codes en `0…`). *Constaté* | 🟡 | Ne jamais tirer de pourcentage d'une tranche ; une tranche sert seulement à vérifier que le code tourne. |
| P-35 | Le nettoyage en un bloc passe sur 32 Go avec seulement 4,9 Go de marge. *Constaté* | 🟠 | Lots par défaut (8) ; un bloc seulement sur machine confortable. |
| P-36 | Versions installées pour le banc d'essai (pandera 0.34, numpy 2.5) plus récentes que celles du TP 9 ; le nettoyage tourne mais rien n'est épinglé. *Constaté* | 🟠 | Rejoint P-01 : épingler `requirements` à partir d'un venv 3.12 où les tests passent. |
