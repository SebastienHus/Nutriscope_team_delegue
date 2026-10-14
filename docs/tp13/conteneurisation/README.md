# Containerisation du pipeline

> À faire **après** que `python -m nutriscope.pipeline all` marche en local (PC 2). On ne met pas dans une boîte un pipeline qui ne tourne pas encore.
> **Statut : préparé, non activé** (décision d'équipe du 14/10 : pas de conteneur pour le J3). Les brouillons
> `Dockerfile`, `compose.yml`, `dockerignore.propose`, `gitattributes.propose` de ce dossier ne sont pas utilisés par le pipeline
> (les deux derniers sont renommés exprès : actifs, ils changeraient le comportement de Docker et de Git).
> Le code du pipeline est déjà compatible : configuration par variables d'environnement, aucune saisie hors terminal,
> chemins relatifs au dépôt, `NUTRISCOPE_GIT_COMMIT`, fuseau Europe/Paris.

## 1. Pourquoi containeriser (et ce que ça ne remplace pas)

Le test « machine vierge » échoue pour trois raisons classiques : une dépendance non déclarée, un chemin propre à ton poste, **un service installé à la main**. Ici, le service oublié, c'est **PostgreSQL** (étape `charger_base`). Un conteneur décrit tout l'environnement (Python 3.12, bibliothèques, base) dans des fichiers versionnés : l'autre équipe tape une commande et obtient le même environnement que toi.

Ça ne remplace pas le README `venv` : l'énoncé le demande, et le poste d'en face n'a peut-être pas Docker.

## 2. Vocabulaire

| Terme | Image mentale |
|---|---|
| **Image** | la recette figée (Python + tes bibliothèques + ton code) |
| **Conteneur** | une exécution de cette recette (jetable) |
| **Dockerfile** | le fichier qui décrit comment fabriquer l'image |
| **Compose** (`compose.yml`) | décrit plusieurs conteneurs qui travaillent ensemble (ici `db` + `pipeline`) |
| **Volume / bind mount** | un dossier partagé entre ta machine et le conteneur : c'est là que vivent les données, pas dans l'image |
| **Healthcheck** | test automatique « la base répond-elle vraiment ? » avant de lancer le pipeline |
| **Variable d'environnement** | réglage passé de l'extérieur (hôte de la base, mot de passe, date) |
| **`.dockerignore`** | ce qui ne doit jamais entrer dans l'image (données, `.git`, `.env`) |

## 3. Architecture

```
          ta machine                                   réseau Compose « nutriscope_default »
 ┌────────────────────────┐                    ┌───────────────────────────────────────────┐
 │ ./data/        (volume)│◄──── monté ───────►│ pipeline  (python -m nutriscope.pipeline) │
 │ ./data-nutriscope (ro) │                    │      │ DB_HOST=db  :5432                  │
 │ .env  (secrets, ignoré)│── variables ──────►│      ▼                                    │
 └────────────────────────┘                    │ db  (postgres:16, volume pgdata, healthcheck)│
                                               └───────────────────────────────────────────┘
```

- Le code est **dans l'image** ; les données sont **dans le volume** (`./data`), hors Git.
- La base a son propre volume (`pgdata`) : elle survit à l'arrêt du conteneur.
- Le pipeline contacte la base par son **nom de service** `db`.

## 4. Pas à pas

1. **Épingler les dépendances** (`requirements-pipeline.txt`, voir P-01) — l'image installe exactement cela.
2. Copier à la racine `Dockerfile`, `compose.yml`, puis `dockerignore.propose` → `.dockerignore` et `gitattributes.propose` → `.gitattributes` ; `cp .env.example .env` et choisir un mot de passe.
3. `docker compose build` — doit réussir sans toucher au réseau pour les données.
4. `docker compose run --rm pipeline all` — démarre la base, attend le healthcheck, exécute les 5 étapes sur l'échantillon.
5. Vérifier sur ta machine : `data/exports/features_nutriscore_<date>.parquet` existe (dossier `data/` monté).
6. Étape seule : `docker compose run --rm pipeline parquet`.
7. Tests : `docker compose run --rm --entrypoint python pipeline -m pytest -q`.
8. **Test machine vierge** : sur un autre dossier, `git clone`, `cp .env.example .env`, étapes 3-4. Si ça passe, tu as prouvé le point 4 de l'énoncé.
9. Tout nettoyer : `docker compose down -v` (supprime aussi la base).

## 5. Ce qu'il faut modifier dans le code pour que ça marche

- `create_database.py` / `nutriscope/config.py` : lire `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` dans l'environnement ; ne jamais appeler `getpass` s'il n'y a pas de terminal (P-09).
- `export_features.git_commit()` : lire `NUTRISCOPE_GIT_COMMIT` avant d'appeler `git` (P-15).
- Date du run : fuseau Europe/Paris (P-14).
- `PYTHONUTF8=1` (déjà dans le Dockerfile) pour les symboles ✓/✗ (P-05).

## 6. Les pièges fréquents (symptôme → cause)

| Symptôme | Cause probable |
|---|---|
| `connection refused` / `could not translate host name "db"` | `DB_HOST=localhost` dans le conteneur, ou le service `db` n'est pas démarré |
| `password authentication failed` | `.env` modifié après le premier démarrage : le volume `pgdata` garde l'ancien mot de passe → `docker compose down -v` |
| `port is already allocated` | un PostgreSQL local occupe 5432 : ne pas publier le port (par défaut), ou utiliser 5433 |
| Le pipeline démarre avant la base | `depends_on` sans `condition: service_healthy` |
| `/bin/sh: ... \r: not found` ou `missing separator` | fins de ligne CRLF → `.gitattributes` + `git add --renormalize .` |
| Build très long à chaque fois | `COPY . .` avant `pip install` ; ou dépendances d'exploration dans l'image |
| Image énorme | données copiées dans l'image → vérifier `.dockerignore` |
| Fichiers de `data/` appartenant à `root` (Linux) | exécution en root dans le conteneur |
| Dates différentes d'une machine à l'autre | fuseau UTC du conteneur → `TZ`, `NUTRISCOPE_DATE` |
| `ZoneInfoNotFoundError` | paquet `tzdata` absent |
| Extrait 13 Go : conteneur tué (`Killed`, code 137) | mémoire allouée à Docker/WSL2 insuffisante → lire par DuckDB, ou monter l'extrait réduit |

## 7. Critères de réussite

- [ ] `docker compose run --rm pipeline all` fonctionne sur un clone frais
- [ ] aucun secret dans l'image ni dans Git (`git ls-files | grep -i env` ne montre que `.env.example`)
- [ ] `docker history <image>` ne montre aucun mot de passe
- [ ] sorties dans `./data/…` sur l'hôte, comptages base = Parquet
- [ ] le README décrit aussi la voie sans Docker
