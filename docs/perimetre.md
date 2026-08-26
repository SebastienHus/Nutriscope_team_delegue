# TP 2 - Définition du périmètre NutriScope

## Contexte

Dans le cadre du projet NutriScope, nous utilisons les données OpenFoodFacts afin de construire un outil d'aide à l'analyse et à la comparaison de produits alimentaires.

Le travail réalisé lors du TP 1 nous a permis d'identifier:
    - un sous-ensemble de produits commercialisés en France (y compris DOM-TOM)
    - réaliser une première exploration du jeu de données.

L'objectif du TP2 est de définir PRECISEMENT le PERIMETRE fonctionnel et technique du projet afin de garantir la faisabilité des développements futurs et la qualité des recommandations produites.

Nous utiliserons donc les data extraites lors du tp1 dans le fichier :
    - ...

 

---

# 1. Profiling du jeu de données

## 1.1 Taille du jeu de données

| Indicateur | Valeur |
|------------|---------|
| Nombre total de produits France | |
| Nombre de colonnes | |
| Taille du fichier | |
| Date d'export OpenFoodFacts | |

### Observations

-

---

## 1.2 Qualité des données

### Taux de remplissage des colonnes principales

| Colonne | Taux de remplissage |
|----------|--------------------|
| product_name | |
| brands | |
| nutriscore_grade | |
| energy_100g | |
| sugars_100g | |
| salt_100g | |
| image_url | |

### Observations

-

---

## 1.3 Cardinalités

### Nombre de valeurs distinctes

| Colonne | Cardinalité |
|----------|------------|
| code | 1136083 |
| product_name | 736670 |
| brands | 113242 |
| categories | ? |
| countries_tags | 4062 |
| nutriscore_grade | 8 |
| energy_100g | 103719 |
| sugars_100g | 13689 |
| salt_100g | 15780 |



### Observations

-

---

## 1.4 Analyse des doublons

### Doublons de codes-barres

| Indicateur | Valeur |
|------------|---------|
| Produits analysés | 1136108 |
| Codes-barres en doublon | 25 |
| Doublons détectés | 0 |

### Exemple(s)

-

### Décision

-

---

## 1.5 Valeurs incohérentes

### Nutriments

| Contrôle | Nombre de cas |
|-----------|--------------|
| sugars_100g > 100 | 49 |
| salt_100g > 100  | 48 |
| energy_100g < 0 | 8 |
| energy_100g = 0 | 17489 |
| energy_100g is nan | 267145 |
| sugars_100g is nan | 274063 |
| salt_100g is nan | 326353 |

### Observations

-

### Décision

-

---

## 1.6 Cohérence des unités

### Colonnes étudiées

-

### Problèmes identifiés

-

### Décision

-

---

# 2. Inventaire des colonnes

## 2.1 Colonnes conservées

### Identification produit

| Colonne | Utilité |
|----------|----------|
| code | |
| product_name | |
| brands | |

### Informations nutritionnelles

| Colonne | Utilité |
|----------|----------|
| nutriscore_grade | |
| energy_100g | |
| sugars_100g | |
| salt_100g | |

### Catégorisation

| Colonne | Utilité |
|----------|----------|
| categories | |
| categories_tags | |

### Images

| Colonne | Utilité |
|----------|----------|
| image_url | |
| image_front_url | |

---

## 2.2 Colonnes écartées

| Colonne | Motif d'exclusion |
|----------|------------------|
| | |
| | |
| | |

---

# 3. Périmètre fonctionnel retenu

## 3.1 Objectif de NutriScope

Décrire ici la fonction principale du produit :

- Analyse nutritionnelle
- Comparaison de produits
- Recherche d'alternatives
- Assistant alimentaire
- Autre

---

## 3.2 Catégories couvertes au lancement

Le formateur recommande un périmètre réduit.

### Catégories retenues

1.
2.
3.
4.
5.
6.
7.
8.

### Justification

-

---

## 3.3 Catégories exclues

| Catégorie | Motif |
|------------|--------|
| | |
| | |
| | |

---

# 4. Critères de sélection des produits

## Conditions minimales

Un produit est conservé si :

- possède un nom ;
- possède un code-barres valide ;
- est commercialisé en France ;
- appartient à une catégorie retenue ;
    Rappel des categories retenue
      - 
- possède un taux minimal d'informations nutritionnelles.

### Seuils retenus

| Critère | Valeur |
|----------|---------|
| Taux minimal de complétude | |
| Nutri-Score obligatoire ? | |
| Image obligatoire ? | |

### Justification

-

---

# 5. Ce que nous n'incluons pas

## Hors périmètre

- Produits non alimentaires.
- Produits sans identification exploitable.
- Produits avec données nutritionnelles insuffisantes.
- Catégories non retenues.

### Pourquoi ?

-

---

# 6. Risques identifiés

| Risque | Impact | Solution |
|----------|---------|----------|
| Données manquantes | | |
| Doublons | | |
| Catégories incohérentes | | |
| Produits étrangers | | |

---

# 7. Décision finale de l'équipe

## Périmètre retenu

-

## Colonnes retenues

-

## Critères de qualité retenus

-

## Arguments principaux

-

---

# Conclusion

Le périmètre retenu permet de concentrer les efforts sur les catégories les plus pertinentes ( qu es ce qu une categorie pertinente pour nous )

Afin de garantir une qualité minimale des données exploitées qualité minimal ne veut pas dire de mauvaise qualité attention !.

autre conclusion selon extraction données .....
