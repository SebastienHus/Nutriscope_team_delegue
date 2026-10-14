# Plan TP 13 — avec « pourquoi » pour chaque étape

Journée : 9h00–17h30. Les durées sont des repères, pas des promesses. Règle d'or : **tout se fait sur l'échantillon** (`data-nutriscope/echantillon_france.csv`, ≈ 8 700 lignes) ; l'extrait complet sert uniquement au tableau des durées.

## Vocabulaire minimal

- **Pipeline** : une chaîne d'étapes qui transforment la donnée, lancée par une seule commande.
- **Orchestration** : décider de l'ordre des étapes, de ce qui se relance, de ce qui est journalisé. Ici = un script Python (la CLI), pas Airflow.
- **Idempotence** : relancer une étape avec les mêmes entrées donne le même résultat (mêmes octets). Sinon impossible de savoir si une différence vient des données ou du hasard.
- **Sortie datée** : `..._20261014.parquet`. Un nouveau jour = nouveau fichier, l'ancien reste.
- **Manifeste** : petit JSON à côté d'une sortie (date, source, empreinte, nombre de lignes). On y met tout ce qui varie (horodatage) pour garder les fichiers de données identiques.
- **`_SUCCESS`** : fichier vide écrit **en dernier** dans un dossier. Absent = écriture interrompue = dossier à ne pas lire.
- **SHA-256** : empreinte d'un fichier. Même empreinte = mêmes octets.
- **Stratifier** : tirer le test dans chaque grade séparément pour garder la même proportion partout (les grades A et B sont rares).
- **Graine** (42) : valeur de départ qui rend un tirage aléatoire reproductible.
- **Source de vérité unique** : la base et le Parquet partent du **même** fichier nettoyé, donc comptent le même nombre de produits.

## Phase 0 — Préparer (09:00–09:30)

1. `git switch develop && git pull`, puis `git switch -c feature/tp13-pipeline`.
2. Recréer un venv **Python 3.12** (ton `.venv` actuel est en 3.14, voir problèmes P-02). **[MAJ 14/10]** Méthode validée : `py install 3.12`, venv **hors** du dossier (`py -3.12 -m venv $env:USERPROFILE\venvs\nutriscope312`), VS Code fermé pendant l'installation, puis toujours appeler `& $PY` (voir P-29).
3. Lancer à la main les 3 commandes existantes sur l'échantillon et noter ce qui marche / casse.
4. Ouvrir `docs/journal_tp13.md`.

*Pourquoi :* on n'assemble que des briques dont on sait qu'elles marchent. Noter l'état de départ évite de chercher un bug du TP 9 dans le code du TP 13.

## Phase 1 — Le point d'entrée (09:30–10:30)

Créer le package `nutriscope/` avec une CLI `python -m nutriscope.pipeline [charger|nettoyer|charger_base|parquet|exports|all]` et la config des chemins (voir `02_conception_module_nutriscope.md`).

*Pourquoi :* aujourd'hui seule la personne qui connaît l'ordre des 3 commandes et leurs options sait produire les données. Une CLI documente ça dans le code.

**PC 1 (partiel)** : `python -m nutriscope.pipeline --help` marche depuis n'importe quel dossier.

## Phase 2 — Les cinq étapes (10:30–12:00)

| Étape | Ce qu'elle fait | Pourquoi elle existe |
|---|---|---|
| `charger` | lit la source **avec DuckDB** (code-barres en texte, 41 colonnes, tri par code), la fige en `data/raw/` + manifeste | prouver de quelles données on part ; **[MAJ 14/10]** 23 s sur le fichier complet au lieu d'une saturation mémoire |
| `nettoyer` | applique les règles du TP 9 (**code inchangé**), en un bloc ou **en lots**, écrit nettoyé + rapport + journal des règles | une seule version de « donnée propre » ; **[MAJ 14/10]** 8 lots = 2,5 Go de pic |
| `charger_base` | recharge PostgreSQL depuis le nettoyé (vide puis remplit) | servir l'application |
| `parquet` | convertit le même nettoyé en Parquet partitionné par rayon + `_SUCCESS` | servir l'analyse et le ML (rapide, typé) |
| `exports` | filtre, ajoute `split`, écrit `features_*.parquet` + `schema.json` | donner à la phase 4 un jeu figé |

Chaque étape **importe** le code existant (`reader`, `cleaning`, `report`, `create_database`, `storage.*`) et retourne : durée, lignes, fichiers écrits.

**PC 1** : `all` sur dossier vide enchaîne les cinq étapes ; comptages base = Parquet.

## Phase 3 — Relançable et idempotent (12:00–13:00, README en parallèle)

1. Dater les sorties ; lire l'entrée du jour sinon la plus récente.
2. Message d'erreur utile : « Aucun nettoyé trouvé : lancez d'abord `nettoyer` ».
3. `_SUCCESS` en dernier ; une étape qui lit un dossier le vérifie.
4. Journal JSON Lines : une ligne par étape, **échecs inclus**.
5. Corriger `convert_parquet` : pas d'`ORDER BY`, donc pas d'idempotence garantie (P-07).

*Pourquoi :* sans ça, « relancer pour réparer » est un pari, et la phase 4 compare des modèles sur des données qui peuvent bouger.

**PC 2** : effacer `data/exports/` → `exports` seule marche ; `parquet` ×2 → mêmes empreintes.

## Phase 4 — Le split (13:00–14:00)

Ajouter la colonne `split` (20 % test par grade, graine 42), compléter `schema.json`, garder le refus d'écraser sans `--force`.

*Pourquoi :* c'est le seul point non rattrapable. Si l'affectation bouge entre le TP 14 et le TP 16, les résultats ne se comparent plus.

**PC 3** : script/test affichant la part de test par grade (5 valeurs ≈ 20 %) et `--force` redonne le même SHA-256.

## Phase 5 — Machine vierge (14:00 → 15:30)

Avant 14:30 : README final. À 14:30 : échange des dépôts. Toi : dérouler leur README **sans leur parler**, noter chaque endroit où tu devines, rendre une liste écrite. Puis corriger chez toi, un commit par correction, message qui dit ce qui manquait.

*Pourquoi :* un pipeline qui ne marche que sur le portable de son auteur n'est pas un livrable. C'est 3 points sur 20.

## Phase 6 — Conteneur (en parallèle ou juste après PC 2)

Voir `04_containerisation.md`. À ne démarrer **qu'après** que le pipeline tourne en local : on ne containerise pas un pipeline cassé.

## Phase 7 — Documentation et tests (15:30–17:00)

- `docs/data/pipeline.md` : schéma du flux, commandes, durées **lues dans le journal**, section « ce que la phase 4 lira ».
- ≥ 12 tests pytest (liste en `02_...`).
- Mesure sur l'extrait complet : lancer **en fin de matinée** pendant que tu écris la doc.

## Phase 8 — Clôture (17:00–17:30)

`python -m pytest -q` vert → `git status` (aucune donnée) → relire ce que `git add` va prendre (évite `git add -A` à l'aveugle, voir P-18) → commit → PR vers `develop` → tag annoté `v0.3` → push du tag.

## Ce qui est facultatif (bonus)

`make extrait`, test comparant deux SHA-256, reprise automatique, conteneur (non exigé par l'énoncé, mais exigé par ton équipe).

## [MAJ 14/10] Durées et volumes de référence (banc d'essai)

À citer dans `docs/data/pipeline.md`, colonne « extrait complet » (Windows 11, 16 cœurs, 32 Go, Python 3.12.10, DuckDB 1.5.6, pandas 2.3.3) :

| Étape | Lignes | Durée | Pic mémoire |
|---|---|---|---|
| `charger` (DuckDB) | 4 535 553 lues, 0 perdue | 23 s | 10,7 Go (plafond 12 Go) |
| `nettoyer` en 1 bloc | 4 535 553 → 996 637 | 2 min 27 s | 14,1 Go |
| `nettoyer` en 8 lots | 4 535 553 → 996 637 | 3 min 08 s | 2,5 Go |

Ces durées viennent du banc d'essai, pas encore du pipeline du TP 13 : les remplacer par celles du journal du
pipeline dès qu'il tourne. Rappel : les tests du pipeline restent sur l'**échantillon** (secondes).
