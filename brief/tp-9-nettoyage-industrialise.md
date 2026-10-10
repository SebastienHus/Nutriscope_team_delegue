# TP 9 — Nettoyage industrialisé · jeu 24/09 (C. Ringot, ½ j après 3.2)

> Module : 3.2 — Nettoyage et préparation des données
> Durée : une demi-journée (13h30 – 17h30), en équipe fil rouge, dans le dépôt Git de l'équipe
> Difficulté : 3 / 5
> Type : TP fil rouge NutriScope — code testé, rapport généré, base rechargée
> Données : l'extrait France de l'équipe (TP 1) ; pour développer et tester vite, `data-nutriscope/echantillon_france.csv` (8 689 produits) — Open Food Facts, © Open Food Facts contributors — ODbL

## Le sujet, tel qu'il figure au Cahier de TP

**Objectif : transformer les recettes de nettoyage du matin en module testé et rejouable.**

1. Créer `src/cleaning.py` : chaque règle de nettoyage devient une fonction pure documentée — normalisation des unités, bornage des nutriments (0–100 g/100 g, énergies plausibles), déduplication des codes-barres, traitement des catégories vides.
2. Stratégie de valeurs manquantes **par colonne et par usage** (supprimer, imputer, garder avec drapeau) — décision écrite, pas implicite.
3. Tests pytest sur chaque règle, y compris les cas tordus relevés au TP 2.
4. Rapport avant/après généré par script : lignes touchées par règle, volumétrie finale.
5. Brancher le nettoyage sur le chargement de la base du TP 4 (la base ne reçoit plus que du propre).

**À committer** : `src/cleaning.py` + tests verts + `docs/data/rapport_nettoyage.md`.

Le reste de ce document détaille ces cinq points. Il n'ajoute aucun livrable.

## Mise en situation

Au TP 2, votre équipe a écrit dans `docs/perimetre.md` que l'extrait France était
sale : sucres à 74 000 g, énergies à 65 600 kcal, 26 codes-barres en double, un
rayon `unknown` qui absorbe un produit sur cinq. Au TP 4, vous avez chargé la base
NutriScope malgré tout, en notant dans le journal que « le nettoyage viendrait ».
Il vient aujourd'hui. La direction (Christophe Ringot, qui joue le client) veut, en
fin d'après-midi, pouvoir lancer une commande qui relit l'extrait brut, applique
des règles écrites, produit un rapport chiffré et recharge la base — et pouvoir la
relancer dans un mois sur un nouvel export sans que personne ne « corrige à la main ».

Ce matin, le module 3.2 vous a donné les briques : le diagnostic (démo 3.2.1), la
stratégie de manquants (exercice 3.2.2), les bornes métier (exercice 3.2.3), le
schéma de validation (exercice 3.2.6) et le contrat « une règle = une fonction pure
+ compte rendu » (section 9). Le TP les assemble dans votre dépôt.

## Objectifs

À la fin de ce TP, votre dépôt contient :

- `src/cleaning.py` : au moins six fonctions pures, une par règle, chacune retournant `(DataFrame, compte rendu)`, avec docstring et constantes métier nommées ;
- `docs/data/strategie_manquants.md` (ou une section de `rapport_nettoyage.md`) : la décision par colonne et par usage ;
- `tests/test_cleaning.py` : au moins un test par règle, un test sur cas tordu, un test d'idempotence — tous verts ;
- `docs/data/rapport_nettoyage.md` : généré par `python -m src.report` (ou équivalent), jamais édité à la main ;
- le script de chargement du TP 4 modifié pour ne recevoir que la sortie du nettoyage, et la base rechargée.

## Prérequis

- Le dépôt d'équipe à jour : `src/`, `tests/`, `docs/`, le script de chargement du TP 4 (`src/load_db.py` ou `sql/`), `.gitignore` excluant les données
- L'environnement Python 3.12 de la formation : pandas 2.3, pytest 9 ; `pd.options.mode.copy_on_write = True` en tête de chaque module
- Les livrables du matin, même partiels : `docs/data/manquants.md`, `strategie_manquants.md`, `exercice_3_2_3.py`, `exercice_3_2_6.py`
- Une règle d'équipe : chaque règle est une branche `feat/cleaning-<regle>`, une pull request, une relecture (TP 3)

## Point de départ

```bash
git checkout dev && git pull
git checkout -b feat/cleaning-squelette
mkdir -p src tests docs/data
touch src/cleaning.py tests/test_cleaning.py
python -m pytest -q          # 0 test, 0 erreur : le squelette est en place
```

Répartition conseillée pour une équipe de trois : une personne sur les règles de
nutriments (unités, bornes, énergie), une sur les règles d'identité (doublons,
textes, catégories) et la stratégie de manquants, une sur le rapport et le
branchement base. Les tests sont écrits par la personne qui **ne** code **pas** la
règle : c'est la relecture la plus efficace.

## Étapes

### Étape 1 — Le contrat commun (20 min)

Définissez dans `src/cleaning.py` :

```python
@dataclass
class CompteRendu:
    regle: str
    lignes_avant: int
    lignes_apres: int
    lignes_touchees: int
    details: dict[str, int] = field(default_factory=dict)
```

et la signature de toute règle : `def regle(df: pd.DataFrame) -> tuple[pd.DataFrame, CompteRendu]`.
Trois obligations : la fonction ne modifie jamais `df` (copie explicite), elle
documente sa règle et ses seuils dans la docstring, les seuils sont des constantes
nommées en tête de module (`KCAL_MAX = 900.0`, `SEL_PAR_SODIUM = 2.5`, `KJ_PAR_KCAL = 4.184`).

Point de contrôle 1 : une règle triviale (`typer_colonnes` : code en `string`,
compteurs en `Int64`, nutriments en `float64`) passe un premier test qui vérifie les
types **et** que l'entrée n'a pas changé (`pd.testing.assert_frame_equal(entree, copie)`).

### Étape 2 — Les règles du point 1 (60 min)

Quatre règles au minimum, dans cet ordre de pipeline :

| Règle | Ce qu'elle fait | Détails à compter |
|---|---|---|
| `normaliser_unites` | kcal ← kJ / 4,184 si absentes ou si le rapport kJ / kcal sort de [3,9 ; 4,5] ; sel ↔ sodium × 2,5 dans les deux sens ; sodium recalculé depuis le sel si incohérent | kcal dérivées, kcal recalculées, sel dérivé, sodium dérivé, sodium recalculé |
| `borner_nutriments` | nutriments négatifs ou > 100 g/100 g → NA (sodium > 40) ; sucres > glucides + 0,5 → sucres NA ; saturés > lipides + 0,5 → saturés NA | par colonne : négatifs, au-dessus de la borne ; sucres, saturés |
| `corriger_energie` | kcal nulles avec macronutriments, kcal > 900, kcal à plus de 50 % du calcul 4 / 4 / 9 (calcul ≥ 50 kcal) → recalcul, sinon NA ; exception : rayon `Alcoholic beverages` ; kJ réalignés | nulles recalculées, > 900 recalculées, > 900 invalidées, incohérentes recalculées |
| `dedupliquer_codes` | code normalisé (espaces), lignes sans code écartées, une fiche par code : la plus complète (`completeness`) puis la plus récente (`last_modified_t`) | sans code, doublons supprimés, codes concernés |
| `traiter_categories_vides` | rayon manquant → `unknown` ; `main_category` dérivée du dernier tag ; drapeau `categorie_vide` ; produits sans catégorie **et** de rayon `unknown` hors périmètre | par sous-règle, inclassables supprimés |

Et, si le temps le permet, `normaliser_textes` (noms vides → NA, noms en
majuscules, marques ramenées à leur graphie la plus fréquente, `unknown` → NA sur les grades).

Point de contrôle 2 : sur l'échantillon partagé, après vos règles, `borner_nutriments`
compte 120 valeurs au-dessus de 100 g, `dedupliquer_codes` retire 26 lignes, et le
diagnostic de la démo 3.2.1 relancé sur la sortie ne trouve plus **aucune** violation de
bornes ni de cohérence sucres / glucides, saturés / lipides, sel / sodium.

### Étape 3 — La stratégie de manquants, point 2 (30 min)

Reprenez `docs/data/strategie_manquants.md` de l'exercice 3.2.2 et implémentez
`strategie_manquants(df, strategie: dict[str, str])` : un dictionnaire
`{colonne: décision}` avec un vocabulaire fermé (`garder`, `drapeau`, `constante:<v>`,
`mediane_rayon`, `mode`, `supprimer_colonne`), plus la suppression des lignes sans
aucun nutriment clé. La stratégie par défaut est **la vôtre**, écrite dans le module
(`STRATEGIE_PAR_DEFAUT`) et dans le document. Une décision inconnue lève `ValueError`.

Point de contrôle 3 : chaque colonne de plus de 10 % de manquants a une ligne dans
le document, avec l'usage et le pourquoi ; le drapeau existe pour les MNAR
(`fiber_100g_manquant`) ; aucune imputation statistique (médiane, KNN) n'est appliquée
ici — elle appartient au pipeline ML, après le split.

### Étape 4 — Les tests, point 3 (40 min)

`tests/test_cleaning.py`, avec une fixture `tordu` : huit à dix produits construits à la
main, un cas tordu par règle, tirés du TP 2 (sucres à 74 000 g, énergie à 24 000 kcal,
sel à 5 000 g, code avec espaces, doublon avec deux complétudes, nom en majuscules,
rayon manquant, ligne sans aucun nutriment). Pour chaque règle :

- un test **nominal** : la règle fait ce que dit sa docstring, et le compte rendu compte juste ;
- un test **cas tordu** : la valeur impossible est traitée comme prévu, la valeur voisine légitime ne l'est pas (900 kcal est à la borne, pas au-delà) ;
- un test **pureté** : l'entrée est intacte après l'appel ;
- un test **idempotence** (paramétré sur toutes les règles, sur l'échantillon réel) : appliquer deux fois donne le même DataFrame et le second compte rendu touche zéro ligne.

Point de contrôle 4 : `python -m pytest -q` : au moins 15 tests, 0 échec, moins de 10 s.

### Étape 5 — Le rapport, point 4 (30 min)

`src/report.py` (ou une fonction de `cleaning.py`) : `generer_rapport(avant, apres, journal, chemin)`
écrit `docs/data/rapport_nettoyage.md` avec : volumétrie avant / après (lignes, colonnes,
codes distincts), lignes touchées par règle (tableau, une ligne par compte rendu, détail des
sous-règles), anomalies métier avant / après (mêmes définitions que le diagnostic du matin),
manquants avant / après sur les colonnes clés, produits par rayon après nettoyage, colonnes
ajoutées et retirées. En tête : la date, la source, le crédit Open Food Facts.

Point de contrôle 5 : le rapport se régénère en une commande ; le supprimer et le relancer
donne le même contenu (à la date près) ; il est committé.

### Étape 6 — Le branchement sur la base, point 5 (30 min)

Le script de chargement du TP 4 reçoit désormais la sortie de `nettoyer(brut)` et rien
d'autre. Deux garde-fous : il **refuse** un DataFrame dont `code` n'est pas unique
(`ValueError`), et le DDL porte des contraintes `CHECK` sur les bornes (0–100 g, 0–900 kcal,
grade dans a–e). Rechargez la base, rejouez les cinq requêtes de contrôle du TP 4 :
volumétrie par table, produits sans catégorie, top marques, complétude Nutri-Score par
rayon, doublons restants (0).

Point de contrôle 6 : `python -m src.pipeline` (ou `make clean-load`) enchaîne lecture →
règles → rapport → base ; le journal indique les volumes par table.

### Étape 7 — Clôture (20 min)

Pull requests fusionnées sur `dev`, tests verts, `docs/journal.md` complété (fait / décidé /
bloqué), démonstration de deux minutes par équipe : la commande, le rapport, une requête
sur la base.

## Conseils

- Ordre des règles : types, textes, doublons, unités, bornes, énergie, catégories, manquants. Les unités **avant** les bornes (un sel dérivé du sodium peut ensuite être borné) ; l'énergie **après** les bornes (le recalcul 4 / 4 / 9 s'appuie sur des macronutriments déjà plausibles).
- Une valeur impossible devient NA, elle ne se tronque pas : 74 000 g de sucres n'est pas 100 g de sucres.
- Le compte rendu compte des **lignes**, pas des cellules : une ligne touchée par trois sous-règles compte une fois dans `lignes_touchees`, trois fois dans `details`.
- `mask` / `where` sur une copie ; jamais `inplace=True`, jamais `df[col][masque] = ...` (chaîne d'affectation, refusée par pandas 3).
- Fixez la date de référence et les graines ; le rapport doit être identique d'une machine à l'autre.
- Si une règle vous semble ambiguë (faut-il garder les codes de 20 chiffres ?), tranchez, écrivez pourquoi dans la docstring, et passez : la direction préfère une décision documentée à une hésitation.

## Dépannage

| Symptôme | Cause probable | Correction |
|---|---|---|
| `SettingWithCopyWarning` ou valeurs non modifiées | affectation en chaîne `df[col][masque] = v` | `df[col] = df[col].mask(masque, v)` sur une copie |
| Le test d'idempotence échoue sur `strategie_manquants` | la règle recrée les drapeaux et les compte comme touchés | compter les lignes dont une valeur a **changé** (comparer avant / après), pas les lignes marquées |
| Le test d'idempotence échoue sur `normaliser_textes` | la capitalisation n'est pas stable (« 1664 BLANC » reste en majuscules) | capitaliser la première **lettre**, pas le premier caractère ; exclure les écritures sans casse (`lower() == upper()`) |
| `TypeError: boolean value of NA is ambiguous` | test `if serie[i]` sur un `Int64` ou `boolean` nullable | vectoriser (`serie.fillna(False)`) ou `pd.isna(v)` |
| Le recalcul 4 / 4 / 9 écrase les boissons alcoolisées | l'alcool apporte de l'énergie que les macronutriments n'expliquent pas | exception explicite sur le rayon, documentée |
| `charger_sqlite` : `UNIQUE constraint failed: produits.code` | doublons non retirés, ou codes avec espaces | `dedupliquer_codes` avant, et refus explicite (`ValueError`) dans le chargement |
| Le rapport diffère d'une exécution à l'autre | date dans le corps, ordre des lignes non fixé | date en en-tête seulement ; tri stable (`kind="stable"`) dans les règles qui trient |
| `pytest` ne trouve pas `src` | exécution hors racine du dépôt | `python -m pytest` depuis la racine, ou `tests/conftest.py` qui ajoute la racine à `sys.path` |

## Grille d'évaluation (sur 20)

| Critère | Points | Observable |
|---|---|---|
| Règles en fonctions pures, documentées, constantes nommées, entrée jamais modifiée | 4 | `src/cleaning.py`, test de pureté |
| Couverture des règles du point 1 : unités, bornes, énergie, doublons, catégories | 3 | comptes sur l'échantillon (120 / 26 / 0 anomalie restante) |
| Stratégie de manquants écrite, par colonne et par usage, implémentée, vocabulaire fermé | 3 | `docs/data/strategie_manquants.md`, `STRATEGIE_PAR_DEFAUT` |
| Tests : nominal, cas tordus du TP 2, pureté, idempotence ; au moins 15, verts | 4 | `python -m pytest -q` |
| Rapport avant / après généré par script, complet, committé | 3 | `docs/data/rapport_nettoyage.md`, régénération identique |
| Branchement sur la base : refus des doublons, contraintes, requêtes de contrôle rejouées | 2 | script de chargement, sortie des cinq requêtes |
| Tenue du dépôt : branches, PR relues, journal, crédit Open Food Facts | 1 | historique Git, `docs/journal.md` |

Seuil de validation de la séance : 10 / 20 avec les tests verts ; un dépôt sans test
vert n'est pas évalué au-delà de 8.

## Ce qui sera repris ensuite

- **TP 10** (30/09, EDA) : l'analyse exploratoire part de la sortie de `nettoyer()`, pas du brut ; les « extrêmes restants » qu'elle examine sont ceux que vos règles ont laissés passer.
- **TP 12** (08/10, Parquet et DuckDB) : la table nettoyée est convertie en Parquet partitionné par rayon ; les cinq requêtes de contrôle sont rejouées en DuckDB ; le Parquet « features » s'appuie sur le dictionnaire des exercices 3.2.5 et de la démo 3.2.3.
- **TP 13** (14/10, jalon J3) : `src/cleaning.py` devient une étape du pipeline `python -m nutriscope.pipeline` ; le rapport est régénéré à chaque exécution ; les jeux train / test sont figés après nettoyage.
- **TP 14** (20/10) : le `ColumnTransformer` de l'exercice 3.2.4 reçoit les données nettoyées ; l'imputation statistique se fait là, après le split.

## Livrable

Dans le dépôt d'équipe, sur `dev`, avant 17h30 : `src/cleaning.py` + tests verts +
`docs/data/rapport_nettoyage.md` (le « À committer » du Cahier), et le script de
chargement du TP 4 branché.