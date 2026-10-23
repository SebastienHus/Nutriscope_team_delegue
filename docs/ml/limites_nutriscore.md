# Note : ce que le modèle Nutri-Score sait et ne sait pas faire

Modèle décrit : XGBoost aux paramètres par défaut, retenu par
[ADR-001](../decisions/ADR-001-modele-nutriscore.md). Toutes les mesures viennent de
`notebooks/ml_nutriscore.ipynb` (sections « Ce que le modèle rate » et « Explication
SHAP »), sur le jeu `nutriscope_ml_sample.parquet` et son split figé : 24 076 produits
en train, 5 965 en test. Le test n'a été ouvert qu'après le choix du modèle.

Seuils du barème 2023 pour les aliments généraux, utilisés pour lire les erreurs :
A ≤ 0, B de 1 à 2, C de 3 à 10, D de 11 à 18, E ≥ 19. Les boissons, les matières
grasses et les fromages ont des grilles spécifiques.

## 1. Ce que le modèle sait faire

**Performance globale**

- F1 macro de 0,894 ± 0,007 en validation croisée (5 plis, sur le train), 0,895 sur le test.
- Accuracy de 0,911 sur le test : 532 erreurs sur 5 965 produits (8,9 %).

**Les erreurs sont presque toujours à un cran.** Pour l'utilisateur, une erreur d'un cran
(b au lieu de c) change peu la décision d'achat ; deux crans ou plus la faussent.

| Écart au bon grade | Erreurs | Part des erreurs | Part du test |
| ------------------ | ------- | ---------------- | ------------ |
| 1 cran             | 478     | 89,8 %           | 8,0 %        |
| 2 crans            | 46      | 8,6 %            | 0,8 %        |
| 3 crans ou plus    | 8       | 1,5 %            | 0,1 %        |

99,1 % des produits du test reçoivent le bon grade ou un grade voisin.

**Le modèle s'appuie sur les composantes du barème.** Classement des features par
contribution SHAP moyenne, tous grades confondus :

1. sel ;
2. graisses saturées ;
3. sucres ;
4. énergie ;
5. protéines ;
6. fibres.

Les sept composantes officielles figurent toutes parmi les onze premières features.
Glucides et lipides totaux, hors barème, apparaissent ensuite : ce sont des proxys des
sucres, des saturés et de l'énergie, pas des fuites. `nova_group` et `additives_n` ne
figurent pas dans les quinze premières : le modèle ne prédit pas le grade à partir du
degré de transformation.

## 2. Les classes difficiles

**Le grade b est la classe difficile.** Les rappels par grade sur le test :

| Grade | Rappel | Part partant vers… |
| ----- | ------ | ------------------ |
| a     | 0,913  | b (5,9 %)          |
| b     | 0,785  | a (10,7 %), c (10,3 %) |
| c     | 0,882  | d (5,6 %)          |
| d     | 0,939  | e (2,9 %)          |
| e     | 0,949  | d (4,7 %)          |

Le grade b fuit des deux côtés, et attire à son tour des a et des c. **46,8 % des erreurs
impliquent b**, comme grade réel ou prédit (249 sur 532), alors que b ne pèse que 10,5 %
du test.

**Deux tiers de ces erreurs sont sur une frontière du barème.** Sur la grille générale,
B ne couvre que deux points de score (1 et 2), contre huit pour C et pour D : chaque
produit B est à un point de A ou de C.

| Confusion   | Produits | Score officiel médian | Exactement sur la frontière |
| ----------- | -------- | --------------------- | --------------------------- |
| b prédit a  | 67       | 1                     | 50,7 % (score 0 ou 1)       |
| b prédit c  | 65       | 2                     | 73,8 % (score 2 ou 3)       |
| a prédit b  | 47       | 0                     | 68,1 % (score 0 ou 1)       |
| c prédit b  | 60       | 3                     | 68,3 % (score 2 ou 3)       |

Le reste ne s'explique pas par la frontière.

- 17 des 67 « b prédit a » ont un score négatif, impossible pour un B de la grille
  générale. Ces produits relèvent d'une grille spécifique (boissons, matières grasses…)
  ou d'une version antérieure du barème. Les features ne portent ni l'une ni l'autre.
- Ces erreurs sont prononcées avec assurance : la confiance moyenne va de 0,65 à 0,68
  selon le sens. **Un seuil de confiance ne suffira donc pas à les écarter** : il faut des
  règles par cas (section 4).

**Le grade b par rayon.** Le rappel de b est le plus faible pour :

- Fruits and vegetables : 0,545, dont 36,4 % partent vers a ;
- Sugary snacks : 0,600 (10 produits seulement) ;
- Composite foods : 0,708.

Il dépasse 0,93 pour les boissons et pour les matières grasses et sauces.

**Deux confusions expliquées par SHAP** (cascades du notebook) :

- **Pâté des Cévennes (3048301401246), b prédit a avec une confiance de 0,997, score
  officiel 1.** Les protéines (26 g) poussent vers a pour +2,67 en log-odds, et le sel
  très bas pour +1,9.
  - Le barème 2023 plafonne les points protéines des viandes rouges, porc compris. Le
    modèle, lui, ne sait pas qu'il s'agit de viande rouge et crédite ces protéines en
    entier : c'est une règle métier absente des features.
  - 0,066 g de sel pour un pâté est en outre invraisemblable : la fiche est probablement
    fausse.
- **Piperade au jambon de Bayonne (3272931005165), b prédit c avec une confiance de
  0,972, score officiel 2.** Le sel (1,5 g) éloigne de b (−2,02), comme les protéines
  faibles (−1,06).
  - La teneur en fruits et légumes est absente de la fiche. Elle est remplacée par la
    médiane, et sa contribution reste faible (−0,21).
  - Le score officiel a pourtant compté des points « légumes » : le modèle n'avait pas
    l'information. Même schéma pour les betteraves rouges (26015460, b prédit c, 0,943).

**Cinq produits sur lesquels le modèle hésite** : ce sont les plus faibles marges entre
les deux grades les plus probables, b/c ou d/e.

| Produit (code) | Score → grade officiel | Prédit (confiance) | Diagnostic | Action |
| --- | --- | --- | --- | --- |
| Dos de cabillaud beurre persil (2250718032345) | 3 → C | b (0,475) | **Limite du modèle** : premier point de C, produit sur la frontière B/C | Limite à documenter : afficher les deux grades voisins (règle 3) |
| Nougat (3760083873751) | 19 → E | e (0,506) | **Limite du modèle** : premier point de E, frontière D/E | Aucune : bonne prédiction, hésitation légitime |
| Merguez bœuf (3018170401531) | 19 → E | e (0,508) | **Règle métier absente** : plafond des points protéines de la viande rouge, qu'aucune feature ne porte | Ajouter une feature « viande rouge » (catégories Open Food Facts) |
| Energy Milk High Protein (7610900066995) | 2 → B | b (0,445) | **Règle métier absente** : les boissons lactées suivent depuis 2023 la grille des boissons ; le modèle ne la connaît qu'à travers le rayon | Ajouter une feature « grille de calcul » (général, boisson, matière grasse, fromage) |
| Filet de haddock sans colorant (2852160024932) | 15 → D | e (0,482) | **Donnée fausse probable** : 316 kcal pour 18 g de protéines et 0 g de sucres, incohérent pour un poisson maigre ; score au milieu de D, donc pas une frontière | Règle de cohérence à ajouter au TP 9 (énergie d'un rayon poisson), vérifier la fiche |

Sur cinq diagnostics, un seul relève de l'apprentissage du modèle (la frontière). Les
autres viennent des données ou de règles du barème que les features ne portent pas.

## 3. Les rayons les moins bien couverts

Performance par rayon sur le test, du pire au meilleur. `n_train` est ce que le modèle a
vu pour apprendre.

| Rayon (`pnns_groups_1`)  | n_train | n_test | F1 macro | Accuracy | Erreurs ≥ 2 crans |
| ------------------------ | ------- | ------ | -------- | -------- | ----------------- |
| Alcoholic beverages      | 33      | 10     | 0,308    | 0,600    | 3                 |
| Fruits and vegetables    | 1 660   | 403    | 0,829    | 0,864    | 10                |
| Sugary snacks            | 5 138   | 1 349  | 0,830    | 0,950    | 6                 |
| Cereals and potatoes     | 2 661   | 603    | 0,844    | 0,854    | 8                 |
| Composite foods          | 2 082   | 494    | 0,856    | 0,887    | 4                 |
| Fat and sauces           | 1 770   | 422    | 0,886    | 0,903    | 3                 |
| Beverages                | 1 762   | 471    | 0,891    | 0,890    | 4                 |
| Fish Meat Eggs           | 4 384   | 1 110  | 0,893    | 0,924    | 5                 |
| Milk and dairy products  | 3 053   | 715    | 0,903    | 0,926    | 7                 |
| Salty snacks             | 1 533   | 388    | 0,915    | 0,918    | 4                 |

- **Alcoholic beverages : non couvert.** 33 produits d'entraînement, F1 macro de 0,31,
  3 erreurs de deux crans ou plus sur 10 produits. Le Nutri-Score ne s'applique d'ailleurs
  pas aux boissons alcoolisées, et le degré d'alcool n'est pas une feature.
- **Fruits and vegetables : couvert, mais fragile sur b.**
  - Le rayon a le plus grand nombre d'erreurs graves (10) et le rappel de b le plus
    faible (0,545).
  - La teneur en fruits et légumes, composante favorable du barème, y manque souvent : le
    modèle impute alors la médiane et perd l'information qui distingue A de B.
- **Sugary snacks : un F1 macro trompeur.** L'accuracy est de 0,950, mais le F1 macro
  tombe à 0,830, tiré par les classes rares du rayon. Il n'y a par exemple que 10 b dans
  le test, dont 4 partent vers c.

## 4. Quand ne pas faire confiance au modèle

Règles destinées au code qui consomme le modèle (API, phase 6). Chacune porte sur des
colonnes disponibles au moment de la prédiction et se vérifie automatiquement.

1. **`pnns_groups_1 == "Alcoholic beverages"` ⇒ ne pas afficher de grade.** Le barème ne
   s'applique pas, et le modèle n'y fait pas mieux qu'un tirage (F1 macro 0,31,
   33 produits d'entraînement).
2. **`energy-kcal_100g == 0` avec `salt_100g > 0`, ou les sept nutriments obligatoires
   tous nuls ⇒ ne pas afficher de grade, signaler la fiche.** La fiche est incomplète :
   par exemple, la sauce Louisiana Gold (0017600023353) affiche 0 kcal et 13 g de sel.
   C'est une règle à ajouter au nettoyage (TP 9).
3. **Grade prédit `b` ⇒ afficher « b, proche de a ou de c ».** 46,8 % des erreurs
   impliquent b alors que b ne pèse que 10,5 % du test, et deux tiers de ces erreurs sont
   à un point de la frontière (section 2).
4. **`pnns_groups_1` dans {"Fruits and vegetables", "Composite foods"} et
   `fruits-vegetables-legumes_100g` manquant ⇒ marquer la prédiction comme incertaine.**
   Sans cette composante favorable, le modèle sous-estime les produits riches en
   légumes : piperade et betteraves rouges, toutes deux prédites c avec plus de 0,94 de
   confiance au lieu de b.
5. **`pnns_groups_2` dans {"Meat", "Processed meat"} et grade prédit `a` ⇒ afficher b au
   mieux, marqué comme incertain.**
   - Le modèle crédite en entier des protéines que le barème plafonne pour la viande
     rouge. Exemples : pâté des Cévennes et viande hachée pur veau, deux B prédits a
     avec plus de 0,97 de confiance.
   - Règle à lever quand une feature « viande rouge » existera.
6. **Écart entre énergie déclarée et énergie calculée par 4/4/9 (`energy_gap_kcal`)
   supérieur à 50 % de l'énergie calculée ⇒ signaler la fiche avant d'afficher le
   grade.** C'est la tolérance du nettoyage (`schema.ENERGY_RELATIVE_TOLERANCE`), que
   le jeu ML partagé n'a pas forcément subie. Une fiche comme celle du filet de haddock
   à 316 kcal (section 2) est à contrôler de cette façon.

Ces règles visent surtout les erreurs prononcées avec assurance. Pour la plupart d'entre
elles, la confiance du modèle ne permet pas de les repérer (section 2).

Données : © Open Food Facts contributors — ODbL.
