================================================================================
          DOCUMENT DE CADRAGE : CRÉATION DU DATASET MAÎTRE OPEN FOOD FACTS
================================================================================

1. HYPOTHÈSE DE DÉPART
--------------------------------------------------------------------------------
* Périmètre géographique : International (Données mondiales).
* Approche : Aucune restriction initiale par pays pour maximiser le volume de données.


2. OBJECTIFS DU PROJET
--------------------------------------------------------------------------------
* Application cible : Application grand public (B2C) facilitant les choix alimentaires au quotidien.
* Stratégie de gestion des données (Dataset Maître) : 
  * Restreindre le jeu de données initial (211 colonnes) à un sous-ensemble optimisé de X colonnes.
  * Conserver les lignes incomplètes dans ce dataset général.
  * Découper ensuite ce dataset général en sous-datasets spécialisés selon la complétude des colonnes (ex: un sous-dataset 100% complet sur la nutrition pour le Machine Learning).
* Cas d'usage Machine Learning (Nutri-Score) :
  1. Isoler un sous-dataset d'entraînement où toutes les variables de l'algorithme officiel sont complètes.
  2. Entraîner un modèle prédictif et comparer ses résultats avec le nutriscore_grade officiel pour valider sa fiabilité.
  3. Déployer le modèle validé sur un second sous-dataset pour prédire les Nutri-Scores manquants.


3. DICTIONNAIRE DES COLONNES SÉLECTIONNÉES
--------------------------------------------------------------------------------

[IDENTIFICATION]
* code : Identifiant unique du produit (code-barres).
* product_name : Nom du produit.
* brands_tags : À privilégier. Identifiants standardisés, normalisés en minuscules et nettoyés (ex: en:nestle au lieu de Nestlé / NESTLE). Idéal pour les jointures et agrégations.
* image_url / image_small_url : Photo générale du produit.
* image_ingredients_url / image_ingredients_small_url : Photo de la liste des ingrédients (audit/Vérification).
* image_nutrition_url / image_nutrition_small_url : Photo du tableau nutritionnel (audit/Vérification).

[CLASSIFICATION]
* main_category : Catégorie principale globale du produit.
* categories_tags : Tags standardisés de toutes les catégories du produit.
* food_groups : Différence avec main_category : main_category est la catégorie précise du produit (ex: en:yogurs). food_groups correspond à la nouvelle nomenclature internationale standardisée d'Open Food Facts (ex: en:dairy-products) qui regroupe les produits de manière plus macro, facilitant les filtres de haut niveau.

[NUTRITION (BASE 100G / 100ML)]
* energy_100g (Énergie)
* fat_100g (Lipides totaux)
* saturated-fat_100g (Acides gras saturés)
* sugars_100g (Sucres)
* fiber_100g (Fibres)
* proteins_100g (Protéines)
* salt_100g (Sel)
* fruits-vegetables-legumes_100g (Taux de fruits, légumes, légumineuses)

[ADDITIFS]
* additives_n : Nombre d'additifs.
* additives_tags : À privilégier. Contient les codes normalisés (ex: en:e951). C'est la seule colonne fiable pour isoler précisément les familles d'additifs (comme les édulcorants de E950 à E969) indépendamment de la langue.

[SCORES OFFICIELS]
* nutriscore_score : Score numérique officiel.
* nutriscore_grade : Lettre officielle (A à E).
* nova_group : Degré de transformation de l'aliment (1 à 4).
* environmental_score_grade : Note d'impact environnemental (Éco-score).

[INDICATEURS DE QUALITÉ]
* completeness : Score de complétude interne à Open Food Facts.
* no_nutrition_data : Indicateur précisant si le produit n'a pas de données nutritionnelles (ex: de l'eau, du sel pur).

[DONNÉES BONUS (FILTRAGE & EXPÉRIENCE UTILISATEUR)]
* ingredients_text : Liste brute des ingrédients.
* allergens / traces : Gestion des risques allergènes.
* countries : Pays de commercialisation.
* quantity : Contenance du produit (ex: "500g", "1.5L").
* labels_tags : À privilégier. Il normalise les labels (ex: en:organic, en:max-havelaar) et évite les doublons liés aux fautes de frappe ou aux langues dans la colonne labels.

[INDICATEUR DE CRÉATION]
* nutriscore_data_complete : Flag booléen indiquant si l'ensemble des 8 colonnes nutritionnelles nécessaires au calcul du Nutri-Score sont remplies.


4. NETTOYAGE ET CORRECTION DES DONNÉES
--------------------------------------------------------------------------------

A. Règles de Nettoyage
* Gestion des spécificités internationales : Le dataset couvrant des données mondiales, le nettoyage doit intégrer le fait que les règles réglementaires et d'affichage diffèrent d'un continent à l'autre (ex: Amérique vs Europe).

* Traitement des codes-barres (EAN) commençant par 200 :
    - Constat : Ces codes correspondent à des produits sans code-barres global standard.
    - Hypothèse de l'équipe : Il s'agit de produits déclassifiés ou inactifs, donc impossibles à proposer comme alternatives de remplacement à l'utilisateur final.
    - Décision initiale : Exclusion de ces produits en première instance.
    - Alerte et action requise : Lancer une vérification quantitative du nombre de codes commençant par 200. ATTENTION : Si le volume de produits impactés est trop élevé, la décision d'exclusion devra être réarbitrée par l'équipe.

* Sélection et optimisation des variables énergétiques :
    - Constat : Pour l'apport énergétique, le jeu de données propose trois colonnes : `energy-kj_100g`, `energy-kcal_100g` et `energy_100g`.
    - Hypothèse de l'équipe : Nous supposions une conversion automatique entre les kilojoules (kJ) et les kilocalories (kcal), faisant de `energy_100g` la valeur finale en kJ nécessaire au calcul du Nutri-Score.
    - Validation technique : L'analyse du code source et des données publiques d'Open Food Facts confirme nos hypothèses. Un algorithme interne effectue la conversion croisée et centralise le résultat en kJ dans `energy_100g`.
    - Décision : Nous nous basons exclusivement sur la colonne `energy_100g` et supprimons les deux autres colonnes afin d'alléger le dataset.
  

B. Règles de Correction
* Principe d'imputation : Identifier et corriger les données manquantes lorsqu'elles peuvent être déduites ou récupérées depuis d'autres colonnes du dataset.
* Arbitrage et contrainte de temps : La priorité reste le retour sur investissement (ROI). Si une tâche de correction s'avère trop complexe par rapport au gain de données espéré, elle ne sera pas réalisée.


1. PRIORISATION DES COLONNES POUR LE MODÈLE NUTRI-SCORE
--------------------------------------------------------------------------------
Pour segmenter efficacement notre jeu de données général, nous définissons un niveau de priorité par bloc de colonnes :

* Priorité 1 (Critique) : Identification + Nutrition + nutriscore_grade
  -> Complétude requise : 100 %
  -> Objectif : Entraînement et validation du modèle de Machine Learning.

* Priorité 2 (Haute) : Identification + Classification + Médias (image_url)
  -> Complétude requise : > 80 %
  -> Objectif : Intégration dans l'application finale pour l'utilisateur.

* Priorité 3 (Secondaire) : Additifs + Données Bonus (labels_tags, allergens)
  -> Complétude requise : Variable
  -> Objectif : Fonctionnalités de filtrage avancé dans l'application.


6. CRÉATION DE NOS PROPRES INDICATEURS (FEATURE ENGINEERING)
--------------------------------------------------------------------------------
Face à l'opacité de l'algorithme completeness d'Open Food Facts (constatée lors des tests sur le code source), l'équipe crée deux indicateurs maison :

1. custom_nutrition_completeness : Score de complétude basé uniquement sur les colonnes indispensables à nos objectifs (notamment le bloc Nutrition pour le ML).
2. nutriscore_data_complete : Indicateur binaire (0 ou 1) validant si la ligne possède 100% des composants nécessaires au calcul du Nutri-Score.
* Note : La colonne completeness d'origine est conservée à des fins d'analyse comparative ultérieure.


7.   