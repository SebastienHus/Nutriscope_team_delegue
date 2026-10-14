# Conception du module `nutriscope/`

> Principe directeur de l'énoncé : **le TP 13 assemble, il ne refait pas.** On importe le code des TP 9 et 12, on ajoute seulement : l'orchestration, les dates, les marqueurs, le journal, le split.

## 1. Structure proposée

```
Nutriscope_team_delegue/
├── nutriscope/                # NOUVEAU — l'orchestration
│   ├── __init__.py            # __version__ = "0.3.0"
│   ├── config.py              # chemins, date du run, graine, variables d'environnement
│   ├── pipeline.py            # CLI (argparse) + fonction run_all()
│   ├── steps.py               # les 5 fonctions d'étape
│   ├── journal.py             # écrire une ligne JSONL par étape
│   ├── manifest.py            # sha256, lire/écrire un manifeste, trouver « le plus récent »
│   └── _legacy.py             # ajoute src/ au sys.path UNE fois (voir §2)
├── src/                       # inchangé (sauf 2-3 correctifs listés en §8)
├── tests/test_pipeline.py     # NOUVEAU — ≥ 12 tests
├── docs/data/pipeline.md      # NOUVEAU
├── docs/journal_tp13.md       # NOUVEAU
├── Makefile                   # façade sur la CLI (optionnel sous Windows)
├── Dockerfile, compose.yml, .dockerignore, .env.example
└── README.md                  # à réécrire
```

## 2. Comment appeler le code existant sans le recopier

Aujourd'hui `src/` s'importe « à plat » (`import cleaning`, `from storage.convert_parquet import ...`), avec des `sys.path.insert` dans plusieurs fichiers. Deux options :

- **A (recommandée aujourd'hui)** : `nutriscope/_legacy.py` ajoute `<racine>/src` au `sys.path` une fois, avec un chemin calculé depuis `__file__`. Zéro déplacement de fichier, zéro risque pour les tests existants.
- **B (dette à noter)** : déplacer `src/` dans `nutriscope/` et réécrire tous les imports + tests. Propre, mais une journée de risque pour rien. À inscrire dans le journal, pas à faire aujourd'hui.

⚠️ Il existe déjà `src/pipeline.py` (TP 9). Comme `src/` sera dans `sys.path`, `import pipeline` désigne **celui du TP 9**, jamais le nouveau. Toujours écrire `nutriscope.pipeline` (jamais `import pipeline`).

## 3. Emplacement des données (tout `data/` est ignoré par Git)

```
data/
├── raw/        produits_bruts_<AAAAMMJJ>.parquet  + .manifest.json
├── clean/      produits_propres_<AAAAMMJJ>.parquet + rapport_nettoyage_<date>.md + regles_<date>.json
├── db/         base_<AAAAMMJJ>.json           (comptes par table : la base elle-même vit dans PostgreSQL)
├── parquet/    produits_<AAAAMMJJ>/pnns_group=<slug>/…  + _SUCCESS + schema_products.json
├── exports/    features_nutriscore_<AAAAMMJJ>.parquet + features_nutriscore_<date>.schema.json
└── logs/       pipeline_journal.jsonl
```

Ton export s'appelle déjà `features_nutriscore_<date>.parquet` : garde ce nom (l'énoncé écrit `features_<date>` à titre générique) et **écris-le dans pipeline.md**.

Variables d'environnement (toutes facultatives, valeurs par défaut sûres) :

| Variable | Défaut | Rôle |
|---|---|---|
| `NUTRISCOPE_SOURCE` | `<racine>/data-nutriscope/echantillon_france.csv` | CSV/Parquet source |
| `NUTRISCOPE_SEP` | `,` | séparateur (`\t` pour l'export complet) |
| `NUTRISCOPE_DATA` | `<racine>/data` | dossier de sorties (les tests mettent un dossier temporaire) |
| `NUTRISCOPE_DATE` | aujourd'hui, **fuseau Europe/Paris** | rejouer une date (P-14) |
| `NUTRISCOPE_DUCKDB_MEMORY` | `12GB` | **[MAJ 14/10]** plafond mémoire de DuckDB à l'étape `charger` |
| `NUTRISCOPE_BATCHES` | `8` | **[MAJ 14/10]** nombre de lots du nettoyage (1 = un bloc) |
| `NUTRISCOPE_GIT_COMMIT` | lu via `git` | dans Docker il n'y a pas de `.git` (P-15) |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` | `localhost`, `5432`, `postgres`, *(obligatoire)* | connexion PostgreSQL, **jamais de saisie interactive** |

Tous les chemins se calculent depuis `Path(__file__).resolve()`, jamais depuis le dossier courant.

## 4. Les fonctions d'étape (même signature)

```python
@dataclass
class StepResult:
    step: str            # "charger", "nettoyer", …
    status: str          # "ok" | "skipped" | "failed"
    rows: int | None     # lignes traitées
    seconds: float
    outputs: list[str]   # fichiers/dossiers écrits (chemins relatifs)
    message: str = ""

def charger(ctx: Context, force: bool = False) -> StepResult: ...
def nettoyer(ctx: Context, force: bool = False) -> StepResult: ...
def charger_base(ctx: Context, force: bool = False) -> StepResult: ...
def parquet(ctx: Context, force: bool = False) -> StepResult: ...
def exports(ctx: Context, force: bool = False) -> StepResult: ...
```

`Context` = chemins + date + graine + paramètres DB, construit une fois par `config.py`.

Squelette d'une étape (pseudo-code, **non testé**) :

```python
def parquet(ctx, force=False):
    t0 = time.perf_counter()
    try:
        entree = find_input(ctx.clean_dir, "produits_propres_*.parquet", step="nettoyer")   # sinon erreur claire
        sortie = ctx.parquet_dir / f"produits_{ctx.run_date:%Y%m%d}"
        if is_complete(sortie) and not force:                     # _SUCCESS présent
            return StepResult("parquet", "skipped", count_rows(sortie), 0.0, [str(sortie)], "déjà fait")
        build_in_tmp_then_rename(entree, sortie)                  # écrit dans sortie.tmp, puis _SUCCESS, puis os.replace
        return StepResult("parquet", "ok", count_rows(sortie), time.perf_counter() - t0, [str(sortie)])
    except StepError as e:
        return StepResult("parquet", "failed", None, time.perf_counter() - t0, [], str(e))
```

`run_all()` appelle les étapes dans l'ordre, **journalise chaque résultat**, s'arrête à la première erreur (code de sortie ≠ 0) et affiche un tableau final (étape, statut, lignes, secondes).

## 5. Détail des étapes

**`charger`** — **[MAJ 14/10]** reprend `bigtest/charger.py` du banc d'essai : DuckDB lit la source en flux
(`read_csv(..., delim='\t', header=true, all_varchar=true, quote='', escape='', ignore_errors=true)`), garde les
41 colonnes de `CONFIG["columns"]`, trie par `code` (puis `last_modified_t`, `product_name`), respecte un plafond
mémoire (`NUTRISCOPE_DUCKDB_MEMORY`, défaut 12GB) et déborde sur disque (`data/tmp/`). Écriture dans un `.tmp`
puis renommage. Sortie : `data/raw/produits_bruts_<date>.parquet` + manifeste (chemin source, taille, séparateur,
nb de lignes lues et écrites, versions, date, empreinte). *Gros fichier :* SHA-256 complet de la **sortie**
Parquet (382 Mo) ; pour la source de 12 Go, empreinte « rapide » (taille + mtime + 1er Mo) marquée `"hash": "fast"`.
Mesuré : 23 s, 0 ligne perdue, 10,7 Go de pic. `reader.read_products` n'est plus utilisé dans ce chemin (dette : à
noter, le TP 9 reste testé tel quel).

**`nettoyer`** — `cleaning.clean(df, DEFAULT_STRATEGY)` + `report.generate_report(...)`. **[MAJ 14/10]** Lit le
Parquet brut ; option `NUTRISCOPE_BATCHES` (défaut 8) : chaque lot = lignes où `hash(trim(code)) % N = i`
(DuckDB), nettoyé seul puis concaténé, trié par `code` avant écriture. Le hachage garantit qu'un même code est
toujours dans le même lot (la déduplication reste juste). Validé : même nombre de lignes qu'en un bloc
(996 637), identique ligne à ligne sur 300 000 lignes. Le rapport est construit en additionnant les `Report` des lots. Écrit le nettoyé en **Parquet** (types conservés ; un CSV perd `Int64`, timestamps…) + rapport Markdown + `regles_<date>.json` (une entrée par règle : nom, lignes modifiées). *Contrôle :* ne rien horodater dans le fichier de données.

**`charger_base`** — `create_database.init_database(...)` puis `load_products(engine, df_nettoye)`. Il rejoue le DDL avec `DROP TABLE IF EXISTS` : le rechargement est complet par construction. Écrit `base_<date>.json` (lignes par table). Contrôle : `products` = lignes du nettoyé.

**`parquet`** — `storage.convert_parquet.to_parquet(source=nettoyé, destination=dossier daté)` enveloppé : écriture dans `.tmp`, `_SUCCESS`, renommage. Contrôle : `count(*)` du Parquet = lignes du nettoyé = `products` en base.

**`exports`** — `storage.export_features.export_features(source=dossier Parquet vérifié, output_dir, force, freeze_date=ctx.run_date)` + split. Si l'export du jour existe déjà : dans `all`, statut `skipped` (pas d'erreur) ; seul `--force` le réécrit.

## 6. Le split : méthode proposée (reproductible produit par produit)

Au lieu d'un tirage aléatoire dépendant d'une bibliothèque, on **trie par empreinte** :

1. Pour chaque grade `a…e`, ordonner ses produits par `md5('42:' || code)` (puis par `code` en cas d'égalité).
2. Les `round(0.20 × n_grade)` premiers sont `test`, les autres `train`.

Avantages : exactement 20 % par grade (arrondi près) ; l'affectation d'un produit ne dépend ni de l'ordre des lignes, ni de la version de numpy/sklearn ; la graine 42 est écrite dans le code **et** dans `schema.json`. Se fait en une fenêtre SQL dans la requête de `export_features.py` :

```sql
split = CASE WHEN row_number() OVER (PARTITION BY nutriscore_grade
                                     ORDER BY md5('42:' || code), code)
                  <= round(0.20 * count(*) OVER (PARTITION BY nutriscore_grade))
             THEN 'test' ELSE 'train' END
```

(*à vérifier* : syntaxe exacte DuckDB et `round` → entier.) Alternative acceptable : `sklearn.model_selection.train_test_split(stratify=..., random_state=42)` après tri par `code` — mais le résultat dépend de la version de scikit-learn : épingle-la si tu la choisis.

À ajouter dans `schema.json` : `split.method`, `split.seed`, `split.test_fraction`, `split.counts_by_grade` (`train`/`test` par grade), `usage_rules` (le texte imposé : *fit sur le train seulement ; test regardé une fois à la fin ; validation croisée dans le train*), et ajouter `split` à `FEATURES` (sinon `describe_export` lève « Exported columns differ »).

## 7. Les 12+ tests (sur l'échantillon, dossiers temporaires, `NUTRISCOPE_DATA=tmp_path`)

1. `charger` crée le brut + manifeste, `code` reste texte (zéros de tête).
2. `nettoyer` crée nettoyé + rapport + règles.
3. `parquet` crée un dossier avec `_SUCCESS` et autant de lignes que le nettoyé.
4. `exports` crée le fichier daté + schéma.
5. `charger_base` : `prepare_tables` sur le nettoyé donne autant de `products` que de lignes (sans PostgreSQL) ; un test marqué `@pytest.mark.skipif` pour la vraie base.
6. Relancer `nettoyer` : même SHA-256.
7. Relancer `parquet` : mêmes empreintes de tous les fichiers.
8. `parquet` sans nettoyé → erreur qui nomme `nettoyer`.
9. `exports` sans Parquet / sans `_SUCCESS` → erreur qui nomme `parquet`.
10. `exports` deux fois sans `--force` → refus ; avec `--force` → même SHA-256.
11. Split : 5 grades, part de test ≈ 20 % (±1 produit).
12. Split : deux exécutions → même affectation **par code**.
13. Le schéma décrit exactement le fichier (colonnes, ordre, `split` inclus, graine 42).
14. Le journal contient une ligne par étape et enregistre aussi un échec.
15. `all` : comptages Parquet = nettoyé (= base si disponible).
16. Aucun chemin absolu dans les fichiers produits (scan des JSON).
17. Crédit ODbL présent dans manifestes/schémas.

## 8. Correctifs minimaux à prévoir dans `src/` (listés en `03_...`)

`convert_parquet.py` : `ORDER BY code` + `SET threads = 1`, garde-fou avant `rmtree`. `export_features.py` : `split`, lecture de `NUTRISCOPE_GIT_COMMIT`. `create_database.py` : mot de passe par variable d'environnement sans `getpass`.
