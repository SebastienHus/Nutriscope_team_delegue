# TP 10 — Analyse exploratoire · mer 30/09 (C. Ringot, ½ j après 3.3)

> Module : 3.3 — Analyse exploratoire approfondie (EDA)
> Durée : une demi-journée en équipe fil rouge, dans le dépôt Git de l'équipe
> Difficulté : 3 / 5
> Type : TP fil rouge NutriScope — notebook narratif exécuté + synthèse d'une page
> Données : périmètre nettoyé au TP 9 (ou l'échantillon partagé avec le nettoyage minimal du module) — © Open Food Facts contributors, ODbL

## Le sujet du Cahier de TP (repris tel quel)

**Objectif : produire l'EDA de référence du projet, celle qu'on citera jusqu'en mars.**

1. Distributions des nutriments clés par rayon : que mange-t-on réellement dans le périmètre choisi ?
2. Complétude et qualité par rayon et par marque : où les données sont-elles fiables, où faudra-t-il être prudent ?
3. Corrélations entre nutriments et Nutri-Score : premiers signaux pour le futur modèle (TP 14) — sans conclure trop vite.
4. Analyse des valeurs extrêmes restantes : vraies (boissons énergisantes) ou résiduelles (erreurs de saisie passées entre les mailles) ?
5. Le tout dans un notebook **narratif** : chaque graphique a un titre-message et trois lignes d'interprétation.

**À committer** : `notebooks/eda_reference.ipynb` + synthèse d'une page dans `docs/data/`.

## Mise en situation

La direction de NutriScope prépare deux échéances : le TP 11 (07/10), où elle veut « l'état du marché alimentaire raconté en graphiques », et le TP 14 (20/10), où l'équipe entraînera le premier modèle de prédiction du Nutri-Score. Entre les deux, elle veut **un document de référence** sur les données du périmètre : ce qu'elles contiennent, où elles sont fiables, ce qu'elles laissent entrevoir. Ce document sera cité au jalon J3 (14/10), dans le rapport EDA du jalon, et encore en janvier devant le jury pour le bloc BC02.

Ce n'est donc pas un brouillon d'exploration : c'est un notebook qui se rejoue de haut en bas, dont les calculs sont dans des fonctions testées, dont chaque figure porte un message, et qui se termine par des décisions. Le module 3.3 vous a donné le gabarit ; l'implémentation de référence du formateur, remise après le TP, le suit sur l'échantillon partagé.

## Objectifs

À la fin de ce TP, votre dépôt contient :

- `notebooks/eda_reference.ipynb`, exécuté sans erreur de haut en bas, sections dans l'ordre des cinq points du Cahier, chaque section au gabarit question → méthode → résultat → trois lignes → décision ;
- `src/eda_lib.py` (ou `src/eda.py`) : les fonctions de calcul réutilisables (profil par rayon, complétude, corrélations, extrêmes), sans affichage ni tracé ;
- `tests/test_eda_lib.py` : au moins dix tests pytest verts sur ces fonctions ;
- `docs/data/synthese_eda.md` : la synthèse d'une page, avec les messages numérotés et le registre d'hypothèses ;
- `docs/data/figures/` (ou `notebooks/figures/`) : les PNG écrits par le notebook, jamais affichés à la main ;
- trois lignes dans `docs/journal.md` : fait, décidé, bloqué.

## Prérequis

- Le module 3.3 (les trois journées) ; en particulier les démos 3.3.1 à 3.3.3 et les exercices 3.3.2, 3.3.3 et 3.3.6
- Le dépôt de l'équipe avec `src/cleaning.py` du TP 9 et sa sortie (le périmètre nettoyé) ; à défaut, l'échantillon partagé `data-nutriscope/echantillon_france.csv` et le nettoyage minimal du module (voir « Point de départ »)
- Environnement Python 3.12 avec pandas 2.3, SciPy, scikit-learn 1.9, matplotlib, pytest, nbconvert ; `pd.options.mode.copy_on_write = True` en tête de chaque module
- Une graine fixée (42) et le backend `Agg` pour matplotlib dans le notebook

## Point de départ

Deux cas, à écrire noir sur blanc en tête du notebook :

- **Cas nominal** : le TP 9 est livré. Le notebook charge la sortie de `src/cleaning.py` (table nettoyée, base du TP 4 ou Parquet intermédiaire) et rappelle en une cellule les règles appliquées et les volumétries (le rapport de nettoyage du TP 9).
- **Cas dégradé** : le TP 9 n'est pas terminé. Le notebook applique un **nettoyage minimal autonome et documenté**, celui du module : doublons de codes-barres (première occurrence gardée), nutriments hors 0-100 g/100 g (ligne écartée), énergie hors 0-900 kcal/100 g (ligne écartée), rayon `pnns_groups_1` manquant ou « unknown » écarté des comparaisons par rayon. Sur l'échantillon partagé : 8 689 → 6 674 produits. Les manquants sont conservés. La cellule dit explicitement que ce nettoyage sera remplacé par celui du TP 9.

Dans les deux cas, le rayon « unknown » est **écarté des comparaisons par rayon** et signalé dans la synthèse (part, complétude) : il représente plus de la moitié de l'extrait complet, le TP 12 devra décider quoi en faire.

## Étapes

### Étape 0 — Ossature et gabarit 

Créez le notebook avec ses sections numérotées (0. Données, 1. Distributions par rayon, 2. Complétude et qualité, 3. Corrélations, 4. Extrêmes restants, 5. Hypothèses et registre, 6. Synthèse) et, dans chaque section, les cinq sous-titres du gabarit. Créez `src/eda_lib.py` avec les signatures des fonctions que vous allez écrire et un premier test qui importe le module. Une fonction utilitaire `figure(fig, nom)` sauvegarde dans `figures/` puis affiche l'image.

Point de contrôle 0 : `jupyter nbconvert --to notebook --execute --inplace notebooks/eda_reference.ipynb` passe sur l'ossature (cellules vides ou presque) ; `python -m pytest -q` passe avec un test.

### Étape 1 — Distributions des nutriments clés par rayon

- `resume_univarie(s)` : effectif, manquants, moyenne, médiane, écart-type, IQR, MAD, CV, asymétrie, aplatissement, quantiles. Appliquez-la à sucres, sel, énergie : une figure (histogrammes avec moyenne et médiane) et trois lignes.
- `profil_par_rayon(df, colonnes, min_n=30)` : médiane, quartiles, moyenne, effectif par rayon et par nutriment ; les rayons de moins de 30 produits sont écartés et listés. Une figure de boîtes triées par médiane (sucres), une figure de barres (sel médian par rayon), chacune avec son titre-message.
- Croisement rayon × grade en % par ligne, V de Cramér ; une figure en barres empilées.

Point de contrôle 1 : trois figures dans `figures/`, trois décisions écrites (par exemple : « le modèle du TP 14 recevra le rayon », « le message d'ouverture du TP 11 est trouvé »). Au moins trois tests sur `resume_univarie` et `profil_par_rayon` (valeurs connues, petit groupe écarté).

### Étape 2 — Complétude et qualité par rayon et par marque

- `completude_par_groupe(df, groupe, colonnes, min_n=20)` : taux de présence de chaque nutriment clé, taux de fiches complètes, présence du score, par rayon puis par marque (marques d'au moins 20 produits).
- `incoherences_metier(df)` : drapeaux booléens par produit (sucres > glucides, saturés > lipides, sel ≠ 2,5 × sodium, énergie déclarée à plus de 150 kcal de l'énergie calculée, énergie nulle avec macronutriments). Comptez, ne corrigez pas.
- Une figure de complétude par rayon, une par marque, un nuage énergie déclarée × énergie calculée.

Point de contrôle 2 : le tableau par marque a ses effectifs ; la décision dit où être prudent (rayons, marques) et quelles règles remontent au TP 9. Au moins trois tests (taux exacts sur un cas synthétique, drapeaux d'incohérence).

### Étape 3 — Corrélations nutriments ↔ Nutri-Score 

- `correlations_nutriscore(df, colonnes, cible, min_n=30)` : Pearson et Spearman de chaque nutriment avec le score, effectifs, tri par |Spearman|. Une figure en barres doubles.
- Matrice de Spearman des nutriments, `paires_redondantes(matrice, seuil=0.8)`, une heatmap exploratoire.
- `correlations_par_rayon(df, colonne, cible)` : la même corrélation dans chaque rayon d'au moins 30 paires ; comparer à la valeur globale pour sucres et sel ; le cas des produits laitiers par sous-rayon.
- Facultatif mais recommandé : ACP sur les nutriments standardisés (variance expliquée, charges, nuage coloré par grade) **en lecture seulement**.

Point de contrôle 3 : la décision liste les features retenues pour le TP 14, les paires tranchées (sodium retiré), et la stratification par rayon. Au moins deux tests (Pearson = 1 sur une relation linéaire, Spearman = 1 sur une relation monotone ; paire sel / sodium détectée).

### Étape 4 — Valeurs extrêmes restantes 

- `zscore_robuste(s)` et `extremes_restants(df, colonnes, seuil=3.5)` : les valeurs à plus de 3,5 MAD de la médiane **de leur rayon**, en format long, triées par |z|.
- Lisez les quinze premières lignes produit par produit et classez-les à la main dans un tableau : vraie (huiles à 900 kcal, sirops à 80 g de sucres, sucres purs, condiments salés) ou résiduelle (eau à 77 g de sel, magret à 25 g, énergie incohérente).

Point de contrôle 4 : la décision propose au moins deux règles supplémentaires pour `src/cleaning.py`, formulées comme des drapeaux. Au moins deux tests (intrus détecté dans un groupe synthétique, résultat vide bien formé).

### Étape 5 — Hypothèses et registre 

- Reprenez les hypothèses de l'exercice 3.3.6 (ou formulez-en quatre) ; vérifiez-en au moins deux avec `comparer_deux_groupes(a, b)` (médianes, d de Cohen, Mann-Whitney), **stratifiées par rayon**.
- Remplissez le registre (hypothèse, méthode, résultat, décision) et exportez-le (CSV ou Markdown) pour la synthèse.
- Écrivez la mise en garde : les tests sont exploratoires, la rigueur inférentielle est vue au 3.4.

Point de contrôle 5 : registre à quatre lignes, au moins une hypothèse rejetée ou reformulée.

### Étape 6 — Synthèse d'une page et rejeu complet 

- `docs/data/synthese_eda.md` : contexte (données, nettoyage, périmètre), six à huit messages numérotés avec leurs chiffres, le registre, les décisions par TP (9, 11, 12, 14), les limites, le crédit Open Food Facts.
- Rejeu complet du notebook avec `nbconvert --execute` depuis un kernel propre ; `pytest` vert ; commit.

Point de contrôle 6 : un coéquipier ouvre le notebook sans vous et retrouve, pour chaque figure, le message dans le titre et la décision dans le texte.

## Conseils

- Écrivez la question **avant** le code de chaque section ; si vous ne savez pas quelle décision une section peut produire, elle ne sert à rien.
- Médianes, quartiles, MAD partout ; la moyenne seulement avec l'écart-type et un commentaire sur les extrêmes.
- Chaque tableau porte ses effectifs (`n`) ; chaque corrélation son `n` et sa méthode.
- Spearman par défaut ; Pearson en plus quand il apporte quelque chose (les huiles).
- Toute corrélation est relue par rayon avant d'entrer dans la synthèse.
- Figures : `matplotlib.use("Agg")`, `fig.savefig(...)`, `plt.close(fig)`, puis affichage du PNG ; pas de `plt.show()`.
- Le notebook ne contient pas de fonctions de calcul : elles vivent dans `src/eda_lib.py` et sont testées.
- Le crédit « © Open Food Facts contributors — ODbL » figure dans le notebook et dans la synthèse.

## Dépannage

| Symptôme | Cause probable | Correction |
|---|---|---|
| `nbconvert` échoue sur `import eda_lib` | le notebook n'est pas lancé depuis le bon dossier | `sys.path.insert(0, "../src")` en tête, ou exécuter depuis la racine du dépôt avec `PYTHONPATH=src` |
| Les figures ne s'affichent pas dans le notebook exécuté | `plt.show()` avec le backend Agg | sauvegarder puis `display(Image(filename=...))` |
| `groupby` renvoie des groupes vides ou un avertissement | rayon en `category` sans `observed=True` | `groupby(..., observed=True)` partout |
| `median_abs_deviation` renvoie `nan` | des NaN dans la série | `s.dropna()` avant |
| Une corrélation par rayon manque | moins de 30 paires complètes | c'est voulu : le dire dans le texte, ne pas baisser le seuil |
| Le V de Cramér dépasse 1 ou vaut `nan` | tableau avec des lignes vides (grades `unknown`, `not-applicable`) | filtrer les grades a-e avant le `crosstab` |
| `SettingWithCopyWarning` ou modification silencieuse | affectation en chaîne | `pd.options.mode.copy_on_write = True` en tête de `eda_lib.py`, pas d'`inplace=True` |
| Le notebook prend plus de deux minutes | UMAP ou t-SNE dans l'EDA de référence | les sortir du notebook de référence (démo 3.3.3) ou les limiter à 2 000 lignes |
