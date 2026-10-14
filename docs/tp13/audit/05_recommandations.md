# Recommandations pour une équipe d'apprenants

## Organisation de la journée

1. **Définition de « fini » écrite au début** : prends les 6 points de contrôle de l'énoncé et la grille à 20 points ; coche au fil de l'eau (`docs/journal_tp13.md`).
2. **Une seule personne tient le clavier sur le cœur** (CLI + étapes), les autres préparent en parallèle : README, tests, `pipeline.md`, conteneur. Changez de rôle après le déjeuner pour que tout le monde comprenne l'ensemble.
3. **Le README avant midi.** C'est le livrable que l'autre équipe jugera, et celui qu'on ne corrige pas après coup.
4. **Chronométrer vos blocages** : 20 minutes sur un bug, puis on demande à l'équipe ou au formateur et on le note dans le journal.
5. **Ne lancez l'extrait de 13 Go qu'une fois**, en fin de matinée, pour le tableau des durées.

## Git, sans casser le dépôt

- Une branche dédiée (`feature/tp13-pipeline`), des commits **petits et nommés** (`feat(tp13): …`, `fix(tp13): …`) comme dans votre `CONTRIBUTING.md`.
- Avant chaque commit : `git status` puis `git diff --staged --stat`. Aucune donnée, aucun `.env`, aucun `.venv`.
- Pas de `git add -A` à l'aveugle (P-18). Pas de `--force` sur Git sans en parler à l'équipe.
- Tag **annoté** : `git tag -a v0.3 -m "Jalon J3"` ; vérifiez avec `git show v0.3` avant `git push --tags`.
- Ajoutez `.gitattributes` **dans un commit séparé** (« normalise les fins de ligne ») : il peut modifier beaucoup de fichiers d'un coup, mieux vaut que ce soit lisible.
- Ne fusionnez pas `feature/docker-compose` (P-17).

## Méthode de travail pour comprendre ce que vous écrivez

- **Lire avant d'écrire** : ouvrez `export_features.py` et expliquez-vous à voix haute ce que fait chaque fonction. Vous allez en importer 6 ou 7.
- **Un petit pas, un test** : écrire une étape, la lancer sur l'échantillon, lire la sortie, puis seulement passer à la suivante.
- **Expliquer pour valider** : si vous ne savez pas expliquer en deux phrases à quoi sert `_SUCCESS` ou pourquoi on trie avant d'écrire, relisez le vocabulaire de `01_plan_tp13.md`. Le jury (et l'autre équipe) posera la question.
- **Comparer des empreintes** : `sha256sum` (Linux/WSL) ou `Get-FileHash` (PowerShell) pour vérifier l'idempotence à la main avant d'écrire le test.
- **Faire échouer exprès** : supprimez une entrée, coupez la base, lancez deux fois `exports`. Un pipeline se juge à ses pannes lisibles.

## Tests

- Tests sur l'**échantillon** uniquement, dans `tmp_path`, jamais sur `data/` réel.
- Une fixture de session qui exécute le pipeline **une fois** et que les tests réutilisent (sinon `pytest` devient lent).
- Un test par promesse de l'énoncé (voir la liste en `02_...`). Nommez-les par ce qu'ils garantissent : `test_exports_refuse_decraser_sans_force`.
- Gardez un test « honnête » : celui qui compare deux exécutions octet par octet est le plus précieux de la journée.

## Sécurité et propreté

- Aucun mot de passe dans Git, dans une image Docker, dans un message de commit ni dans un `-pwd` en ligne de commande.
- `.env` ignoré ; `.env.example` versionné avec des valeurs factices.
- Le crédit « © Open Food Facts contributors — ODbL » dans chaque fichier produit (manifestes, `schema.json`, rapport, README).
- Rien de personnel dans les journaux ou les schémas (chemins `C:\Users\...` = fuite et non-portabilité : le test n°16 les cherche).

## Test « machine vierge »

- Faites-le **vous-mêmes avant l'échange**, dans un dossier neuf, sans réutiliser votre venv : `git clone`, nouveau venv Python 3.12, `pip install -r requirements-pipeline.txt`, la commande.
- Notez chaque endroit où vous avez deviné — c'est la liste que vous rendrez à l'autre équipe, par écrit.
- Quand vous recevez leur liste, corrigez **un commit par problème**, avec un message qui dit ce qui manquait (« README : ajoute l'étape de création du venv »).
- Préparez les deux voies (venv et Docker) et dites laquelle vous recommandez.

## Pour `docs/data/pipeline.md`

- Plan : (1) schéma du flux en texte, avec qui lit quoi (la base sert l'application, le Parquet sert l'analyse et le ML) ; (2) commandes ; (3) durées mesurées avec machine et versions ; (4) « ce que la phase 4 lira » (nom du fichier, schéma, interdits).
- Les durées viennent du **journal JSONL**, pas de votre mémoire. Copiez la ligne du journal en annexe.
- Terminez par 2-3 phrases de lecture : quelle étape domine, pourquoi, et si un orchestrateur se justifie (spoiler probable : non, un Makefile/une CLI suffit encore).

## Ce que vous pourrez dire au jury / au formateur

- *Pourquoi pas Airflow ?* Flux de quelques secondes ; un orchestrateur ajoute un service à maintenir pour un problème que nous n'avons pas.
- *Pourquoi trier avant d'écrire ?* Pour que deux exécutions donnent les mêmes octets.
- *Pourquoi stratifier ?* Les grades A/B sont rares ; sans stratification un grade peut quasiment disparaître du test.
- *Pourquoi `_SUCCESS` ?* Un dossier sans lui est un dossier à moitié écrit.
- *Pourquoi Docker ?* Pour que la base et Python soient décrits dans des fichiers au lieu d'être installés à la main.

## Pistes pour la suite (hors J3)

Reprise automatique d'un pipeline interrompu, `make extrait`, split dérivé en `train.parquet`/`test.parquet`, intégration continue (GitHub Actions) qui lance `pytest` sur chaque PR, renommage de `src/` en package.

## [MAJ 14/10] Leçons du banc d'essai

- **Mesurer avant de supposer** : on pensait que le problème venait des colonnes ; la mesure a montré que c'était la façon de lire (pandas + `pd.concat`).
- **Une tranche teste le code, pas les chiffres** : le fichier étant trié par code, les premières lignes donnaient 10 % de lignes gardées au lieu de 22 %.
- **Lire attentivement les options** : `--rows 300000 --batches 4` = 300 000 lignes en 4 lots, pas 4 × 300 000.
- **Sous Windows** : un terminal = ses variables (`$PY`, `$SRC`) ; un venv = un chemin à vérifier (`sys.executable`) ; VS Code ouvert peut verrouiller un venv.
- **Prouver l'équivalence** quand on change la façon de calculer (lots vs bloc) : raisonnement + comparaison ligne à ligne sur un extrait + comptage sur le total.
- **Garder la trace des décisions** (« tous les pays ») avec leur date et leurs conséquences sur les autres documents.
