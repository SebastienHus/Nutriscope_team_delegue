# 3. Analyse des risques

## Objectif

Cette analyse vise à identifier les principaux risques susceptibles d'affecter la qualité des données, la pertinence des résultats et le bon fonctionnement de la solution NutriScope.

Chaque risque est évalué selon :

- sa probabilité d'occurrence ;
- son impact sur le projet ;
- les mesures de mitigation envisageables.

---

## Risque R1 : Données nutritionnelles incohérentes

### Description

Certaines fiches produits peuvent contenir des valeurs nutritionnelles incohérentes ou aberrantes :

- sucres supérieurs à 100 g pour 100 g ;
- sel supérieur à 100 g pour 100 g ;
- énergie négative ;
- valeurs manquantes ou erronées.

### Probabilité

Élevée

### Impact

Élevé

### Niveau de risque

🔴 Critique

### Plan de mitigation

- Mise en place de contrôles qualité automatiques.
- Détection et exclusion des valeurs aberrantes.
- Règles de validation avant exploitation des données.
- Contrôles réguliers sur les données importées.

---

## Risque R2 : Produits incomplets

### Description

Certains produits disposent d'un code-barres mais présentent peu d'informations exploitables :

- ingrédients absents ;
- valeurs nutritionnelles manquantes ;
- nom du produit absent ;
- Nutri-Score indisponible.

### Probabilité

Élevée

### Impact

Moyen

### Niveau de risque

🟠 Important

### Plan de mitigation

- Filtrer les produits insuffisamment renseignés.
- Définir un seuil minimal de qualité des données.
- Informer l'utilisateur lorsque l'analyse est incomplète.
- Afficher un indice de fiabilité du résultat.

---

## Risque R3 : Hétérogénéité des données

### Description

Les données provenant d'Open Food Facts peuvent présenter différentes nomenclatures ou formats pour une même information.

Exemples :

- pays exprimés sous plusieurs formats ;
- tags multiples pour une même catégorie ;
- conventions de nommage variables.

### Probabilité

Élevée

### Impact

Moyen

### Niveau de risque

🟠 Important

### Plan de mitigation

- Normaliser les données lors de l'import.
- Créer des référentiels internes.
- Uniformiser les valeurs avant traitement.
- Mettre en place des règles de nettoyage automatisées.

---

## Risque R4 : Dépendance à Open Food Facts

### Description

La majorité des informations exploitées provient d'une source externe unique.

Une indisponibilité ou un changement de structure pourrait impacter le fonctionnement de la solution.

### Probabilité

Moyenne

### Impact

Élevé

### Niveau de risque

🟠 Important

### Plan de mitigation

- Mise en cache locale des données.
- Sauvegarde régulière des informations essentielles.
- Historisation des produits déjà consultés.
- Prévoir l'intégration d'autres sources de données à moyen terme.

---

## Risque R5 : Non-conformité RGPD (Changement de réglementation)

### Description

Les préférences alimentaires, allergies ou intolérances peuvent être considérées comme des données sensibles nécessitant une vigilance particulière.

### Probabilité

Faible

### Impact

Élevé

### Niveau de risque

🟠 Important

### Plan de mitigation

- Limiter les données collectées au strict nécessaire.
- Recueillir le consentement explicite des utilisateurs.
- Permettre la modification ou la suppression des données.
- Mettre en œuvre une politique de confidentialité transparente.

---

## Risque R6 : Recommandations peu pertinentes

### Description

Les recommandations produites peuvent manquer de pertinence lorsque les informations produit ou utilisateur sont insuffisantes.

### Probabilité

Moyenne ( selon moyen alloué pour entrainer un model )

### Impact

fort ( ref a reputation de l appli )

### Niveau de risque

🟠 Important

### Plan de mitigation

- Réaliser des tests utilisateurs réguliers.
- Ajuster les règles métier de recommandation.
- Améliorer progressivement la personnalisation.
- Recueillir les retours utilisateurs afin d'affiner les suggestions.

---

# 4. Matrice Probabilité × Impact

![img](matrice-risques.jpg)

---

# 5. Synthèse des risques

| ID | Risque | Probabilité | Impact | Niveau |
|----|---------|-------------|--------|---------|
| R1 | Données nutritionnelles incohérentes | Élevée | Élevé | 🔴 Critique |
| R2 | Produits incomplets | Élevée | Moyen | 🟠 Important |
| R3 | Hétérogénéité des données | Élevée | Moyen | 🟠 Important |
| R4 | Dépendance à Open Food Facts | Moyenne | Élevé | 🟠 Important |
| R5 | Non-conformité RGPD | Faible | Élevé | 🟠 Important |
| R6 | Recommandations peu pertinentes | Moyenne | Moyen | 🟠 Important |

---

# Alternative plan de mitigation

## Risque R1 : Données nutritionnelles incohérentes

### Constat

Certaines données issues d'Open Food Facts peuvent contenir des valeurs aberrantes ou incohérentes :

- sucres supérieurs à 100 g pour 100 g ;
- sel supérieur à 100 g pour 100 g ;
- énergie négative ;
- valeurs manifestement erronées.

### Solutions envisagées

#### Option 1 : Correction automatique

Corriger ou remplacer automatiquement les valeurs incohérentes.

Avantages :

- Conservation d'un plus grand volume de données.

Inconvénients :

- Risque d'introduire de nouvelles erreurs.
- Altération potentielle de la donnée d'origine.

#### Option 2 : Isolation des données incohérentes

Conserver les données mais les exclure de certains traitements.

Avantages :

- Préservation de la donnée brute.
- Réduction des risques sur les modèles.

Inconvénients :

- Complexification des traitements.

### Solution retenue

Les produits présentant des incohérences majeures seront exclus des jeux d'entraînement et de validation des modèles prédictifs.

Les données concernées seront conservées à des fins d'audit mais non utilisées dans les calculs ayant un impact direct sur les recommandations.

### Justification

La qualité des données est prioritaire pour garantir la fiabilité des modèles et limiter la propagation d'erreurs dans les analyses.

---

## Risque R2 : Produits incomplets

### Constat

Certains produits disposent d'informations partielles :

- ingrédients absents ;
- Nutri-Score manquant ;
- valeurs nutritionnelles incomplètes.

### Solutions envisagées

#### Option 1 : Rejet systématique

Refuser toute analyse lorsque certaines données sont absentes.

Avantages :

- Résultats très fiables.

Inconvénients :

- Nombre important de produits non exploitables.

#### Option 2 : Analyse partielle

Exploiter les données disponibles lorsque les informations essentielles sont présentes.

Avantages :

- Couverture plus importante du catalogue.

Inconvénients :

- Niveau de précision variable.

### Solution retenue

Lorsque les informations critiques sont disponibles, le produit reste analysable.

En cas de données secondaires manquantes, l'application affiche un indice de confiance permettant à l'utilisateur d'évaluer la fiabilité du résultat.

### Justification

Cette approche préserve l'expérience utilisateur tout en restant transparente sur les limites de l'analyse proposée.

---

## Risque R3 : Hétérogénéité des données

### Constat

Certaines informations sont représentées sous plusieurs formats :

- noms de pays ;
- catégories ;
- tags ;
- unités de mesure.

### Solutions envisagées

#### Option 1 : Traitement manuel

Corriger progressivement les incohérences détectées.

Avantages :

- Mise en œuvre rapide.

Inconvénients :

- Peu scalable.

#### Option 2 : Normalisation automatisée

Uniformiser les données lors de leur importation.

Avantages :

- Traitement homogène.
- Réduction des anomalies futures.

Inconvénients :

- Développement initial plus important.

## Risque R4 : Dépendance à Open Food Facts

### Constat

La plateforme repose principalement sur les données provenant d'Open Food Facts.

Une indisponibilité du service, une évolution de son modèle de données ou une dégradation de la qualité des informations pourrait impacter directement NutriScope.

### Solutions envisagées

#### Option 1 : Consommation directe

Interroger Open Food Facts à chaque demande utilisateur.

Avantages :

- Données toujours à jour.
- Pas de stockage local important.

Inconvénients :

- Forte dépendance à un service tiers.
- Impact direct en cas d'indisponibilité.

#### Option 2 : Réplication locale

Conserver une copie locale des données utiles.

Avantages :

- Réduction de la dépendance.
- Meilleures performances.

Inconvénients :

- Nécessite une synchronisation régulière.

#### Option 3 : Multiplication des sources

Combiner plusieurs bases de données alimentaires.

Exemples :

- Open Food Facts
- CIQUAL
- Bases partenaires

Avantages :

- Réduction du risque de dépendance.

Inconvénients :

- Complexité d'intégration plus importante.

### Solution retenue

Mise en cache locale des produits les plus consultés et synchronisation périodique avec Open Food Facts.

L'architecture devra permettre l'ajout futur d'autres sources de données.

### Justification

Cette approche limite les risques liés à une source unique tout en conservant un niveau raisonnable de complexité pour le projet.

---

## Risque R6 : Recommandations peu pertinentes

### Constat

La qualité des recommandations dépend directement :

- de la qualité des données d'entraînement ;
- du volume de données disponibles ;
- de la représentativité des données ;
- de la qualité des profils utilisateurs ;
- des règles métier utilisées.

Un modèle entraîné sur des données incomplètes, bruitées ou biaisées peut produire des recommandations peu pertinentes.

### Solutions envisagées

#### Option 1 : Modèle prédictif dès le démarrage

Utiliser rapidement un modèle d'apprentissage automatique.

Avantages :

- Potentiel de personnalisation élevé.

Inconvénients :

- Risque de mauvaises recommandations.
- Sensibilité forte à la qualité des données.

#### Option 2 : Approche hybride

Combiner règles métier et IA.

Avantages :

- Recommandations plus explicables.
- Réduction des erreurs.

Inconvénients :

- Développement plus important.

#### Option 3 : Approche progressive

Commencer par des règles métier fiables puis introduire progressivement des modèles prédictifs.

Avantages :

- Réduction du risque.
- Contrôle plus simple des résultats.

Inconvénients :

- Personnalisation limitée au début.

### Solution retenue

Dans un premier temps, les recommandations seront basées principalement sur des règles métier transparentes et explicables.

L'utilisation de modèles prédictifs sera envisagée uniquement après :

- nettoyage des données ;
- validation de leur qualité ;
- constitution d'un historique suffisant ;
- évaluation des performances obtenues.

Les produits présentant des données incohérentes ou aberrantes seront exclus des jeux d'entraînement afin d'éviter l'introduction de biais dans les modèles.

### Justification

La confiance de l'utilisateur repose principalement sur la pertinence des recommandations.

Privilégier d'abord la qualité des données et l'explicabilité permet de sécuriser le fonctionnement de la plateforme avant d'introduire des mécanismes d'apprentissage plus avancés.


## Synthese plan de mitigation 

## Synthèse des stratégies de mitigation retenues

| Risque | Solutions étudiées | Solution retenue | Justification |
|----------|-------------------|------------------|---------------|
| **R1 - Données nutritionnelles incohérentes** | Correction automatique, exclusion des données incohérentes | Exclusion des données aberrantes des jeux d'entraînement et des calculs métier | Garantir la qualité des analyses et limiter l'introduction de biais dans les modèles prédictifs |
| **R2 - Produits incomplets** | Rejet systématique, analyse partielle | Analyse partielle lorsque les données critiques sont présentes avec affichage d'un indice de confiance | Améliorer la couverture du catalogue tout en restant transparent sur la qualité des résultats |
| **R3 - Hétérogénéité des données** | Traitement manuel, normalisation automatisée | Normalisation automatique lors de l'import et utilisation de référentiels internes | Garantir l'homogénéité des traitements et réduire les anomalies liées aux formats multiples |
| **R4 - Dépendance à Open Food Facts** | Consommation directe, réplication locale, multi-sources | Cache local avec synchronisation périodique et architecture ouverte à d'autres sources | Réduire la dépendance tout en conservant des données à jour et de bonnes performances |
| **R6 - Recommandations peu pertinentes** | Modèle prédictif immédiat, approche hybride, approche progressive | Règles métier dans un premier temps puis introduction progressive de modèles prédictifs | Sécuriser la qualité des recommandations avant d'introduire des mécanismes d'apprentissage plus complexes |

---

## Principes directeurs retenus

| Principe | Application dans NutriScope |
|-----------|----------------------------|
| Qualité avant quantité | Les données incohérentes sont exclues des entraînements et analyses critiques |
| Transparence | Affichage d'un indice de confiance lorsque certaines informations sont manquantes |
| Normalisation systématique | Contrôle et harmonisation des données avant exploitation |
| Réduction des dépendances | Mise en cache locale et préparation à l'intégration d'autres sources |
| IA progressive et maîtrisée | Priorité aux règles métier explicables avant l'introduction de modèles complexes |
| Amélioration continue | Réévaluation régulière des données, modèles et recommandations |

---

# Conclusion

L'analyse met en évidence un risque critique et plusieurs risques importants principalement liés à la qualité, à la complétude et à la disponibilité des données. Ces risques sont directement liés à l'utilisation d'une source de données ouverte et collaborative telle qu'Open Food Facts.

Les mesures de mitigation identifiées permettent toutefois de réduire significativement leur impact en s'appuyant sur des mécanismes de contrôle qualité, de normalisation, de sécurisation des données et d'amélioration continue de la plateforme.