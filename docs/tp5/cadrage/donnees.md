# Qualification des données - NutriScope

# Contexte

NutriScope repose sur l'exploitation de données alimentaires afin d'accompagner le consommateur dans sa prise de décision lors de l'achat d'un produit.

Cette étude vise à inventorier les sources de données nécessaires au fonctionnement du projet, à évaluer leur pertinence et leur qualité, puis à identifier les risques associés à leur utilisation.

---

# 1. Inventaire des sources de données

## Source 1 : Open Food Facts

### Description

Base collaborative recensant les caractéristiques de millions de produits alimentaires.

### Données exploitées

- Code-barres
- Nom du produit
- Marque
- Catégories
- Nutri-Score
- Valeurs nutritionnelles
- Ingrédients
- Allergènes
- Images

### Usage dans NutriScope

Source principale pour l'identification et l'analyse des produits.

---

## Source 2 : Étiquetage industriel

### Description

Informations fournies directement par les fabricants.

### Données exploitées

- Liste des ingrédients
- Valeurs nutritionnelles
- Allergènes
- Labels
- Mentions réglementaires

### Usage dans NutriScope

Source primaire alimentant indirectement Open Food Facts.

---

## Source 3 : Utilisateur

### Description

Informations saisies ou générées lors de l'utilisation.

### Données potentielles

- Produits scannés
- Préférences alimentaires
- Allergies déclarées
- Questions posées à l'assistant

### Usage dans NutriScope

Personnalisation des recommandations.

---

## Source 4 : Historique des scans

### Description

Journal des recherches effectuées dans l'application.

### Données exploitées

- Produit consulté
- Date de consultation
- Fréquence de consultation

### Usage dans NutriScope

Amélioration de l'expérience utilisateur.

---

## Source 5 : Référentiel interne NutriScope

### Description

Base enrichie par l'application.

### Données exploitées

- Produits comparables
- Scores calculés
- Recommandations générées
- Résultats d'analyse IA

### Usage dans NutriScope

Accélération des traitements et enrichissement fonctionnel.

---

# 2. Qualification des sources selon les 5 portes

## Source : Open Food Facts

| Porte | Verdict | Commentaire |
|---------|----------|------------|
| Disponible ? | ✅ Oui | Base publique facilement accessible |
| Accessible ? | ✅ Oui | Accès via export ou API |
| Qualité suffisante ? | ⚠️ Partiellement | Présence de données manquantes et incohérences constatées lors du TP2 |
| Légale ? | ✅ Oui | Données publiques |
| Utile ? | ✅ Oui | Source centrale du projet |

---

## Source : Étiquetage industriel

| Porte | Verdict | Commentaire |
|---------|----------|------------|
| Disponible ? | ✅ Oui | Présent sur les produits |
| Accessible ? | ✅ Oui | Informations réglementaires |
| Qualité suffisante ? | ✅ Oui | Source officielle déclarative |
| Légale ? | ✅ Oui | Données publiques |
| Utile ? | ✅ Oui | Source primaire des informations nutritionnelles |

---

## Source : Utilisateur

| Porte | Verdict | Commentaire |
|---------|----------|------------|
| Disponible ? | ✅ Oui | Collecte possible |
| Accessible ? | ✅ Oui | Via formulaire ou paramètres |
| Qualité suffisante ? | ⚠️ Variable | Dépend de ce que renseigne l'utilisateur |
| Légale ? | ⚠️ Sous conditions | RGPD et consentement nécessaires |
| Utile ? | ✅ Oui | Permet la personnalisation |

---

## Source : Historique des scans

| Porte | Verdict | Commentaire |
|---------|----------|------------|
| Disponible ? | ✅ Oui | Généré automatiquement |
| Accessible ? | ✅ Oui | Interne à la plateforme |
| Qualité suffisante ? | ✅ Oui | Traçabilité fiable |
| Légale ? | ⚠️ Sous conditions | Conservation à encadrer |
| Utile ? | ✅ Oui | Amélioration des services |

---

## Source : Référentiel NutriScope

| Porte | Verdict | Commentaire |
|---------|----------|------------|
| Disponible ? | ✅ Oui |
| Accessible ? | ✅ Oui |
| Qualité suffisante ? | ✅ Oui |
| Légale ? | ✅ Oui |
| Utile ? | ✅ Oui |

---

# 3. Principaux risques qualité Open Food Facts

Les analyses réalisées lors du TP2 ont montré plusieurs limites de qualité des données.

## Risque n°1 : Données manquantes

Exemples observés :

- energy_100g manquant
- sugars_100g manquant
- salt_100g manquant
- nutriscore_grade absent

### Impact

Impossible de produire certaines analyses ou recommandations.

---

## Risque n°2 : Valeurs incohérentes

Exemples observées lors du TP2 :

- sugars_100g > 100
- salt_100g > 100
- energy100g < 0

### Impact

Résultats erronés.

# 5. Risques liés aux données

## Risque n°1 : Données nutritionnelles incohérentes

Certaines valeurs nutritionnelles peuvent être erronées ou dépasser les limites physiologiquement plausibles.

Exemples :

- sucres supérieurs à 100 g pour 100 g ;
- sel supérieur à 100 g pour 100 g ;
- énergie négative.

### Impact

- Résultats d'analyse erronés.
- Recommandations incorrectes.
- Perte de confiance des utilisateurs.

### Mesure

Mise en place de contrôles qualité automatiques lors de l'import des données.

--

# Risque n°2 : Produits incomplets
Certains produits possèdent un coe-barres mais comportent peu d'infrmations exploitables.

Deschamps importants peuvent être absnts :

- nomdu produit ;
- énergie;
 sucres ;
- sel ;
- ingrédients

### Impact

- Exprience utilisateur dégradée.
- Anayse impossible ou incomplète.
-Recommandtions moins pertinentes

### Mesure

Identifieret filtrer les produitsprésentant trop de données manquanes.

--

## Risque n°3 : Hétéogénéité des données Open Food Facs

L'analyse du jeu de donnéesa montré quOpen Food Facts utilise des nomenlatures parfois très variées,notamment pour les informations gégraphiques et les tags associés au produits. 1-0786fc】

### Impact

- Difficult à filtrer correctement les produis.
- Résltats incohérents lors des analyse.
- Traitements supplémentaires néessaires.

### Mesure

-Normalisation des valeurs.
- Crétion de référentiels internes.
 Contrleslors de l'import desdonnées.

---

# Risque n°4 : Données non mises àjour

Les informationsdisponibles dansles bases partenaires peuvent évoler :

- changement de formulation 
- modification des ingrédients ;
 évolution du Nutri-Score ;
- corrction de données.

### Impact

- Rcommandations obsolètes.
- Mauaisequalité de service

### Mesure

- Synchronsation régulière avec Open Food Fats.
- Rechargement périodique des onnées.

---

#Risque n°5 : Dépendance à Open Foo Facts

Une grandepartie des données exploitées provent d'Open Food Facts.

### Impact
- Déendance à une source externe.
- Diponibilité potentiellement affecté.
-Évolutiondu modèle de données.

### Mesure
- Miseen cachelocale des données.
- Historisatio des produits consultés.
- Possbilité d'ajouter d'autres sources  terme.

---

# Risque n°6 :Qualité de la personnalisation

Le recommandations déendent en partie des informations ournies par l'utilisateur

### Impact

- Reommandations peu pertinentes.
 Personnalisation limitée.

### Meure

- Paramtrage facultatif du profil.
- Possbilité demodifier les préférences à tout moent.
- Transparence sur les critèrs utilisés.

---

## Risquen°7 : Conformité RGPD

ême avecune collecte limitée, certaines inormations peuvent être considéréescomme sensibles lorsquelles concernent l'alimentation, ls allergies ou les restrictions almentaires.

### Impact

- Risques églementaires.
- Perte de confianc des utilisateurs.

### Mesure

- rincipe de minimisation des donnée.
- Consentement explicite.
- Consrvation limitée des informations.
 Politique de confidentialité tranparente.

---

## Synthèse des risues identifiés

| Risue | Impact | Mesre envisagée |
|----------|---------|----------------|
| Données nutitionnelles incohérentes | Élevé |Contrôles qualité automatisés |
| roduits incomplets | Élevé | Filtrge des données manquantes |
| Hétéogénéité des données | Moyen | Noralisation et référentiels internes|
| Données non mises à jour | Moyn | Synchronisation régulière |
| épendance à Open Food Facts | Moye | Mise en cache et diversificatio des sources |
| Personnalisation imitée | Moyen | Paramétrage utiliateur facultatif |
| Risques RGPD  Élevé | Consentement et minimisaton des données |

# 6. Conclusion

L'analyse du processus actuel met en évidence plusieurs difficultés rencontrées par les consommateurs lors du choix d'un produit alimentaire. Malgré la présence d'informations nutritionnelles sur les emballages et l'existence d'applications spécialisées, l'interprétation des données, la comparaison des produits et la prise de décision restent souvent complexes, notamment dans un contexte d'achat où le temps est limité.

L'étude des processus AS-IS et TO-BE montre qu'une approche fondée sur l'intelligence artificielle peut contribuer à simplifier l'accès à l'information et à améliorer l'expérience utilisateur. En automatisant certaines tâches d'identification, d'analyse, d'explication et de recommandation, NutriScope permet de transformer des données nutritionnelles parfois difficiles à exploiter en informations claires et directement utiles à la prise de décision.

Au-delà de la réponse apportée aux besoins des consommateurs, le projet présente également des opportunités pour les professionnels de la nutrition, les acteurs de la prévention santé, les distributeurs et les industriels agroalimentaires. La plateforme peut ainsi s'inscrire dans un écosystème plus large visant à favoriser une meilleure compréhension de l'alimentation et des choix nutritionnels.

Enfin, les pistes d'évolution identifiées démontrent que NutriScope pourrait progressivement enrichir ses services grâce à la personnalisation, à l'assistance conversationnelle, à l'analyse de profils alimentaires ou encore à l'intégration de nouvelles sources de données. Le projet présente donc un potentiel réel de création de valeur tout en répondant à une problématique concrète rencontrée quotidiennement par de nombreux consommateurs.