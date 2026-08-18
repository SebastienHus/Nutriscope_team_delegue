Justification du choix du jeu de données


Les données utilisées proviennent du projet OpenFoodFacts disponible à l'adresse :
https://world.openfoodfacts.org/data

Plusieurs formats de données sont proposés :

Un dump complet MongoDB de plus de 14 Go.
Des fichiers au format Parquet.
Plusieurs exports CSV segmentés par domaine.

Après analyse, le dump MongoDB a été écarté en raison de son volume important.
Le format Parquet a également été étudié. Bien qu'il présente de bonnes performances pour les traitements analytiques, les temps de chargement observés sur la machine de développement se sont révélés plus importants que souhaité pour les phases exploratoires.
Nous avons donc retenu l'utilisation des exports CSV mis à disposition par OpenFoodFacts. Ces exports sont déjà répartis en plusieurs catégories :

- Produits alimentaires
- Produits cosmétiques
- Produits pour animaux
- Autres produits

Cette première segmentation permet déjà de réduire considérablement le volume de données à traiter. Le choix s'est naturellement porté sur le fichier consacré aux produits alimentaires, ce qui représente une économie d'environ 5 Go de données par rapport à l'ensemble des exports disponibles.

Première phase d'exploration
Avant toute phase de nettoyage ou d'analyse, une première extraction a été réalisée afin d'identifier les principales colonnes exploitables pour l'étude.
L'objectif était de vérifier la présence des informations essentielles :

Identifiant produit (code)
Nom du produit (product_name)
Pays de commercialisation (countries)
Marque (brands)
Informations nutritionnelles :

Énergie (energy_100g)
Sucres (sugars_100g)
Sel (salt_100g)


Indicateur de disponibilité des données nutritionnelles (no_nutrition_data)

Pour réaliser cette première lecture du fichier, nous avons utilisé DuckDB, particulièrement adapté à la manipulation directe de fichiers CSV volumineux sans nécessiter de base de données intermédiaire.
Cette étape a également permis de générer les premiers fichiers de travail destinés aux traitements ultérieurs.

Compréhension des données de localisation
Dans un premier temps, nous nous sommes basés sur la colonne countries afin de filtrer les valeurs associées à la France. Cependant, les résultats étaient trop disparates et difficiles à interpréter. Les libellés n'étaient pas suffisamment cohérents pour permettre un filtrage fiable.
Nous nous sommes donc orientés vers la colonne countries_tags, dont les valeurs sont davantage normalisées.
Pour cela, il a d'abord fallu comprendre le fonctionnement de la normalisation utilisée par OpenFoodFacts.
Les données ne reposent pas uniquement sur des codes pays normalisés (ISO), mais sur un ensemble de tags de localisation multilingues. Ces tags suivent généralement la structure suivante :

<langue>:<zone_geographique>

Identification des produits français
L'objectif final étant de travailler uniquement sur les produits commercialisés en France, nous avons retenu les principes suivants :

Un produit français est sélectionné.
Un produit étranger commercialisé en France est également sélectionné, car il est susceptible d'être consommé par un consommateur français.
Les territoires d'outre-mer (DOM-TOM) ne sont pas oubliés et sont intégrés au périmètre de sélection.

Cette extraction a mis en évidence un point important : chaque enregistrement peut contenir plusieurs pays simultanément.
Il n'était donc pas possible de filtrer directement les données sans disposer au préalable d'une liste exhaustive des valeurs uniques existantes.

Construction de la liste complète des tags pays
Afin d'identifier toutes les valeurs de pays présentes dans la base, chaque ligne a été analysée puis éclatée sur le séparateur ,.
Les différentes valeurs rencontrées ont ensuite été stockées dans un ensemble (set) permettant d'éliminer automatiquement les doublons.
Cette approche a permis de construire progressivement un référentiel complet des tags pays utilisés dans OpenFoodFacts.
Les valeurs collectées ont ensuite été exportées dans un fichier CSV nommé :
liste_pays_uniques_tag.csv

Nettoyage des valeurs collectées
Une phase complémentaire de nettoyage a été appliquée afin de :

supprimer les guillemets parasites ;
retirer les espaces inutiles ;
éliminer les éventuels doublons résiduels ;
ordonner les valeurs par ordre alphabétique.

Analyse des tags de localisation
L'analyse du fichier obtenu a montré qu'OpenFoodFacts utilise une nomenclature très hétérogène.
On retrouve aussi bien :

des pays ;
des régions ;
des regroupements de pays ;
des territoires d'outre-mer ;
des traductions multilingues d'une même zone géographique.

La dernière phase a consisté à interpréter manuellement ces différents codes afin d'identifier les valeurs devant être associées au périmètre français.
Cette étape a permis de constituer une liste de références fiable pour le filtrage final.

Résultat obtenu
Grâce à cette analyse des tags de localisation, nous pouvons désormais filtrer les produits commercialisés en France et constituer un jeu de données cohérent pour les traitements futurs.
Le jeu de données final conserve notamment les colonnes suivantes :

Nom du produit (product_name)
Pays de commercialisation (countries)
Marque (brands)
Énergie (energy_100g)
Sucres (sugars_100g)
Sel (salt_100g)

Ce jeu de données servira de base aux prochaines phases de nettoyage, d'analyse statistique et d'exploitation des données nutritionnelles.

Cinq  questions  à  résoudre  en  équipe  :  

    - combien  de  produits  vendus  en  France  ?
    Nous avons trouvé 1 136 108 produits vendus en France et DOM-TOM. Nous avons retiré les produits qui n'ont aucun nom.

    - quelle  part  a  un  Nutri-Score renseigné  ?
    55.09% sont renseignés.

    - les  dix  marques  les  plus  présentes  ?  
    Carrefour       15121
    Auchan          13569
    U               11856
    Leader Price     5422
    Casino           5071
    Cora             3935
    Le Gaulois       3418
    Picard           3405
    Nestlé           3310
    Monoprix         3260

    - le  taux  de  manquants  sur  les  nutriments  clés  ( energy_100g , sugars_100g ,  salt_100g ) ?
    energy_100g : 0.2351
    sugars_100g : 0.2412
    salt_100g : 0.2873

    - qu'est-ce qui vous semble le plus « sale » dans ces données ?
    Les données sont très hétérogènes. Nous retrouvons plusieurs langues dans les descriptions des produits.
    Les régions de France sont segmentées par DOM-TOM, origine des produits et destination. Il est très difficile de trier à partir d'un pays particulier.
    Le .csv renseigne plus de colonnes que le .parquet notamment en ce qui concerne les valeurs nutritionnelles. Ce n'est pas le cas du .parquet qui regroupe le tout en une seule colonne "nutriments". Il existe donc des différences structurelles entre les différents fichiers de données ce qui empêche leur interchangeabilité.