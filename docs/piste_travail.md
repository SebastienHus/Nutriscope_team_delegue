1 - Hypothese on tape sur la totalite du jeu de donnée onne se base pour le moment pas sur un pays unique 

2 - Objectifs recuperer le jeu de donnée de base et le restreindre selon les colonnes que nous jugeon interessante
l objectif principal est de creer une application pour l utilisateur final mr et madame tout le monde 
[ rappel de l objectif de nutriscope ]

nous restreignons le nombre de colonne a x colonne
ce nouveau data set presente des ligne incomplete sur les colonne selectione cela nous permettra de decouper ce nouveau data set general en d autre data set plus specifique selon completude des colonnes 
exemple en cas de creation de ml pour creer un nutriscore il nous faudra absolument tout les colonne nutritionelle qui entre d ans l algo  de nutriscore ainsi nous pourron entraine un modele que nous comparerons au nutriscore deja renseigné qui nous permettra de juger de la fiabilite de notre modele 
par la suite on pourra recupere un autre jeu de donné pour predire les nutriscore manquant ect 
le but de ce jeu de donnée general et d etre propre et de ne pas nous limiter dans les futur operations que nous auront a mener
il sera juste a specialiser

3 - Explication des colonnes selectionné
dans un premier temps nous avons souhaiter comprendre ce que contenait les 211 colonnes e base de nutriscope nous avond donc generer un dictionnaire
ce documentnous a permis de faire une analyse en equipe selon nos objectif ( voir point 2) pour savoir quelles colonne nous garderont
[explication]

Identification :

- code
- product_name
- brands
- brands_tag ( peut etre a privilegier par rapport a brands  ? )
- image_url
- image_small_url
- image_ingredients_url
- image_ingredients_small_url
- image_nutrition_url
- image_nutrition_small_url

Classification :

- main_category
- categories_tags
- food_groups ( quelle dif avec main category ? )

Nutrition :

- energy-kj_100g
- fat_100g
- saturated-fat_100g
- sugars_100g
- fiber_100g
- proteins_100g
- salt_100g
- fruits-vegetables-legumes_100g

Additif : ( le quel choisir ?)

- additives_n
- additives 
- additives_tags ( je pencherai pour lui )

Scores :

- nutriscore_score
- nutriscore_grade
- nova_group
- environmental_score_grade

Qualité :

- completeness
- no_nutrition_data

Bonus :

- ingredients_text
- allergens
- traces
- countries
- quantity
- labels_tags
- labels ( entre lui et tag lequel garder )

Creation :

- nutriscore_data_complete


4 - Netoyage et correction des data

a - netoyage
pour nettoyer la data selon les colonne precedente selectionné nous avons besoin de comprendre certaine regle metier 
car nous ne sommes pas mono pays mais sur des donnée mondiale un regle en amerique n est pas la meme qu en europe ou autre 

voici les regle que nous identifions pour le nettoyage de la donnée 

- pour les ean 

attention particuliere sur les ean qui commence par 200 correspond a des produit sans code bar 
interpretation( hypothese )  
correspondrai a des produits qui serait declassifié donc plus actif donc pas possibilite de le proposer en remplacement 
donc on choisi de ne pas les prendre en premiee instance --> verification du nombre de code bar qui commence par 200
ATTENTION si trop de produit sans code bar decision a prendre !

autre regle a suivre

b - correction 
Nous nous apercevons dans notre data set que certaine information manquant pourraient etre renseigné car celles ci sont presente dans d autre colonne

nous souhaiton donc corrigee les données manquante ci possible
la contrainte est le temps si une tache est trop compliqué par rapport au gain esperer nous ne la realiseront pas

5 - priorisation des colonnes

pour nos objectif nous priorison les colonne par ordre d importance dans leur role pour accompir nos objectif cite en point 2 
exemple dans l objectif de creer un nutris score nous avons absolument besoin pour un sous data set que les donne nutritionelle soient remplis a 100% ainsi que le nutriscore deja defini par open food fact pour comparer nos resultats
donc un taux de 100% de completude sera determine

liste l ordre de priorite / completude determiner pour chaque colonne


6 - creation de nos propre indicateurs 

Suite a la priorisation des colonne et pour specialiser notre jeu de donné nous souhaitons creer nos propre indicateurs
- Filtrer les produit que l on vas prndre 
hypothese 1 se baser sur completeness qui correspond au taux de completion des données legale obligatoire et autre que open food fact juge comme determiante 

pb nous n arrivons pas a savoir exactement quels colonne entre en ligne de compte pour l algo meme apres recherche dans code sources
nous avns tester avec les donnée parcelaire collecte sur leur site et des fichiers de test sur leur code source sans parvenir aux meme resultats 

donc nous partons sur la creation de deux indicateur 
- notre propre colonne taux de completion selon les colonne qui nous jugeons utiles pour la suite exemple les colonne de nutrition pour futur entrainement de ml
- nous garderons cependant la colonne completeness pour les analyse futur


7 - 



 

 


