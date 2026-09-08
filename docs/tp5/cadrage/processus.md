# Cartographie du processus métier NutriScope

## Contexte

NutriScope est une application d'aide à la décision alimentaire destinée aux consommateurs.

Elle permet de scanner un produit alimentaire, d'analyser ses caractéristiques nutritionnelles et de fournir une explication simple ainsi que des alternatives plus adaptées aux besoins de l'utilisateur.

L'objectif de cette étude est de comprendre le processus actuel suivi par un consommateur lors de l'achat d'un produit alimentaire, d'identifier les difficultés rencontrées et de montrer comment l'intelligence artificielle peut améliorer cette expérience.

# Pèrimetre du parcours

- **Processus étudié** : Du scan d'un produit en rayon jusqu'à la décision d'achat ou le choix d'un substitut plus sain.
- **Persona ciblé (Cœur de cible)** : Sophie Martin (38 ans, assistante administrative, parent soucieuse de l'alimentation familiale, très pressée en magasin).
- **Contexte d'usage** : Directement en magasin dans les rayons alimentaires (ex: céréales petit-déjeuner). La décision doit se prendre en quelques secondes sans jargon ni culpabilisation.

---

# 1. Processus AS-IS (Situation actuelle)

## Description

Aujourd'hui, un consommateur souhaitant faire un choix alimentaire éclairé peut s'appuyer sur plusieurs sources d'information : les étiquettes présentes sur les emballages, le Nutri-Score lorsqu'il est affiché, ainsi que des applications spécialisées telles que Yuka ou Open Food Facts.

Malgré l'existence de ces outils, certaines difficultés demeurent. Les informations nutritionnelles peuvent être complexes à interpréter pour une partie des consommateurs. Les données sont parfois dispersées entre plusieurs sources, ce qui oblige l'utilisateur à effectuer ses propres recherches ou comparaisons.

Par ailleurs, les besoins nutritionnels varient selon les individus, leurs objectifs ou leurs contraintes de santé. Les informations actuellement disponibles ne répondent pas toujours de manière personnalisée à ces situations particulières.

Enfin, le temps disponible lors d'un achat en magasin est souvent limité, ce qui peut rendre difficile l'analyse approfondie et la comparaison de plusieurs produits avant de prendre une décision.

---

## Acteurs du processus

- Consommateur
- Produit alimentaire
- Étiquette nutritionnelle
- Applications concurrentes (Yuka, Open Food Facts, etc.)
- Internet

---

## Déroulement du processus

### Étape 1 : Choix d'un produit

Le consommateur repère un produit en rayon.

### Étape 2 : Lecture des informations

Il consulte :

- la liste des ingrédients ;
- le tableau nutritionnel ;
- le Nutri-Score lorsqu'il est présent ;
- les éventuels labels ou mentions.

### Étape 3 : Compréhension

Il tente d'interpréter les informations nutritionnelles.

### Étape 4 : Recherche complémentaire

Lorsque les informations sont insuffisantes ou difficiles à comprendre, il peut :

- consulter internet ;
- utiliser une application spécialisée ;
- comparer plusieurs produits.

### Étape 5 : Décision

Le consommateur décide d'acheter ou non le produit.

---

## Frictions identifiées

| ID | Friction | Impact |
|----|-----------|---------|
| F1 | Difficulté à comprendre les informations nutritionnelles | Élevé |
| F2 | Temps nécessaire pour comparer plusieurs produits | Élevé |
| F3 | Informations parfois incomplètes ou absentes | Moyen |
| F4 | Absence de recommandations personnalisées | Élevé |
| F5 | Multiplication des sources d'information | Moyen |
| F6 | Décision prise sous contrainte de temps en magasin | Élevé |

---

# 2. Processus TO-BE (Avec NutriScope)

## Description

Avec NutriScope, la plupart des tâches d'analyse sont automatisées.

L'utilisateur obtient en quelques secondes une synthèse claire du produit ainsi que des recommandations adaptées à son profil et à ses objectifs.

---

## Acteurs

- Consommateur
- Application NutriScope
- Base Open Food Facts
- Base NutriScope
- Moteur IA

---

## Déroulement du processus

### Étape 1 : Scan du produit

L'utilisateur scanne le code-barres du produit.

### Étape 2 : Recherche

L'application récupère les informations disponibles dans la base de données.

### Étape 3 : Analyse IA

Le moteur IA :

- analyse les données nutritionnelles ;
- identifie les points forts et faibles du produit ;
- prépare une synthèse simplifiée.

### Étape 4 : Recommandation

L'application propose :

- une explication compréhensible ;
- des alertes éventuelles ;
- des alternatives mieux notées ;
- une aide à la comparaison.

### Étape 5 : Décision

L'utilisateur dispose immédiatement des informations nécessaires pour prendre une décision éclairée.

---

# 3. Comparaison AS-IS / TO-BE

| Critère | AS-IS | TO-BE |
|----------|--------|--------|
| Compréhension des données | Complexe | Simplifiée |
| Temps d'analyse | Plusieurs minutes | Quelques secondes |
| Comparaison des produits | Manuelle | Automatisée |
| Recommandations | Absentes | Présentes |
| Personnalisation | Faible | Élevée |
| Confort utilisateur | Moyen | Élevé |

---

# 4. Interventions de l'intelligence artificielle

## IA n°1 : Identification du produit

### Fonction

Reconnaître rapidement le produit scanné.

### Données utilisées

- Code-barres
- Base Open Food Facts

### Valeur apportée

Accès immédiat aux informations produit.

---

## IA n°2 : Analyse nutritionnelle

### Fonction

Analyser automatiquement la qualité nutritionnelle du produit.

### Données utilisées

- Calories
- Sucres
- Matières grasses
- Sel
- Fibres
- Protéines

### Valeur apportée

Évaluation rapide de la composition du produit.

---

## IA n°3 : Génération d'explications

### Fonction

Transformer des données techniques en recommandations compréhensibles.

### Exemple

Au lieu d'afficher uniquement :

"17 g de sucres pour 100 g"

l'application peut afficher :

"Ce produit contient une quantité élevée de sucre. Une consommation régulière doit être modérée."

### Valeur apportée

Améliore la compréhension pour tous les profils d'utilisateurs.

---

## IA n°4 : Recommandation de produits alternatifs

### Fonction

Identifier des produits similaires présentant un meilleur profil nutritionnel.

### Valeur apportée

Facilite les choix plus équilibrés.

### Exemple

L'utilisateur consulte une pâte à tartiner.

L'application suggère une alternative contenant moins de sucre et davantage de protéines.

---

# 5. Analyse des opportunités

## Opportunité métier

Les consommateurs sont de plus en plus sensibles à leur alimentation mais disposent rarement du temps ou des connaissances nécessaires pour analyser correctement les informations nutritionnelles.

NutriScope répond à ce besoin en fournissant une aide rapide, simple et accessible.

---

## Bénéfices pour l'utilisateur

- Gain de temps.
- Meilleure compréhension des produits.
- Comparaison facilitée.
- Choix plus éclairés.
- Découverte d'alternatives plus adaptées.

---

## Bénéfices pour l'organisation

- Valorisation de l'usage de l'IA dans un contexte concret.
- Création d'un service à forte valeur ajoutée.
- Possibilité d'enrichir progressivement les fonctionnalités.
- Différenciation par rapport aux solutions existantes.

---

# 6. Conclusion

L'analyse du processus actuel met en évidence plusieurs difficultés rencontrées par les consommateurs lors du choix d'un produit alimentaire : compréhension complexe des données nutritionnelles, manque de temps, comparaison difficile et absence de personnalisation.

Grâce à l'intelligence artificielle, NutriScope automatise les tâches d'analyse, simplifie l'information et accompagne l'utilisateur dans sa prise de décision. Le projet présente donc une réelle opportunité d'amélioration de l'expérience utilisateur tout en démontrant la valeur ajoutée d'une approche IA appliquée au domaine de la nutrition.


----


