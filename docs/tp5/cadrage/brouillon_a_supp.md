# NutriScope — Structuration du Backlog : Epics & User Stories

Ce document présente la décomposition fonctionnelle du projet NutriScope. Pour respecter la méthode Agile et les principes INVEST, les User Stories ont été atomisées (une seule responsabilité par US) et regroupées au sein de 4 Epics majeurs.

---

## 1. Vue d'ensemble des Epics

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EPIC 1 : DATA PIPELINE                          │
│        (Ingestion, Nettoyage & Qualification du catalogue OFF)         │
└──────────────────────────────────┬─────────────────────────────────────┘
│
├── US-05a : Pipeline de nettoyage DuckDB
└── US-05b : Log & Audit des rejets Data

┌────────────────────────────────────────────────────────────────────────┐
│                        EPIC 2 : ENGINE & IA                            │
│           (Scoring prédictif, Substituts & Transparence)               │
└──────────────────────────────────┬─────────────────────────────────────┘
│
├── US-02a : Prédiction du Nutri-Score (ML)
├── US-02b : Calcul de l'indice de confiance
├── US-03  : Moteur de recommandation d'alternatives (KNN)
├── US-06b : Gestion du seuil d'incertitude (< 50 %)
└── US-07  : Volet d'explicabilité du calcul

┌────────────────────────────────────────────────────────────────────────┐
│                   EPIC 3 : CORE USER EXPERIENCE                        │
│               (Accessibilité produit & Consultation)                   │
└──────────────────────────────────┬─────────────────────────────────────┘
│
├── US-01a : Consultation par Scan EAN
├── US-01b : Consultation par Recherche textuelle
└── US-02c : Explication non culpabilisante

┌────────────────────────────────────────────────────────────────────────┐
│                     EPIC 4 : CONVERSATIONAL RAG                        │
│                    (Assistant Nutritionnel IA)                         │
└──────────────────────────────────┬─────────────────────────────────────┘
│
└── US-04 : Question / Réponse vulgarisée sur le produit

```

---

## 2. Matrice de traçabilité (Epics vs US)

| Epic | Réf US | Titre de la User Story | Composante / Valeur |
| :--- | :--- | :--- | :--- |
| **Epic 1** | **US-05a** | Ingestion & Nettoyage Data | Pipeline DuckDB rejouable |
| **Epic 1** | **US-05b** | Rapport d'audit des rejets | Qualification et traçabilité de la donnée |
| **Epic 2** | **US-02a** | Prédiction du Nutri-Score | Modèle Scikit-learn (Nouveau calcul 2023/2024) |
| **Epic 2** | **US-02b** | Indice de confiance Data | Calcul de fiabilité du score |
| **Epic 2** | **US-03** | Recommandation de substituts | Moteur KNN (1 à 3 produits plus sains) |
| **Epic 2** | **US-06b** | Gestion du seuil d'incertitude | Blocage des prédictions si confiance < 50 % |
| **Epic 2** | **US-07** | Volet d'explicabilité | Transparence sur les nutriments réels vs estimés |
| **Epic 3** | **US-01a** | Scan de code-barres | Appel API REST direct via EAN (< 500 ms) |
| **Epic 3** | **US-01b** | Recherche textuelle | Moteur de recherche par nom de produit |
| **Epic 3** | **US-02c** | Fiche produit pédagogique | Restitution neutre et non culpabilisante |
| **Epic 3** | **US-06a** | Gestion des produits inconnus | Message d'absence et signalement produit |
| **Epic 4** | **US-04** | Assistant RAG | QA conversationnel avec garde-fous éthiques |

---

## 3. Spécification détaillée des User Stories

### Epic 1 : Data Pipeline

#### US-05a : Pipeline automatisé d'ingestion et de nettoyage
* **En tant que** : Lead Data Engineer.
* **Je veux** : Exécuter un script d'ingestion rejouable sur le snapshot Open Food Facts.
* **Afin de** : Filtrer les doublons d'EAN et éliminer les valeurs nutritionnelles aberrantes (ex. sucre > 100g, énergie négative).
* **Critères d'acceptation** :
  * Le pipeline s'exécute de manière automatisée via DuckDB / Python.
  * Seules les données valides alimentent la base nettoyée.

#### US-05b : Log et audit des rejets Data
* **En tant que** : Lead Data Engineer.
* **Je veux** : Générer un rapport d'audit à l'issue de l'exécution du pipeline.
* **Afin de** : Identifier et quantifier le volume de fiches produits corrompues ou exclues.
* **Critères d'acceptation** :
  * Les lignes rejetées sont consignées dans un fichier de log d'audit avec la raison du rejet.

---

### Epic 2 : Engine & IA

#### US-02a : Modèle prédictif du Nutri-Score
* **En tant qu'** : Utilisateur consultant un produit sans score officiel.
* **Je veux** : Obtenir un Nutri-Score estimé par l'IA.
* **Afin de** : Évaluer la qualité globale d'un produit aux données incomplètes.
* **Critères d'acceptation** :
  * L'estimation s'appuie sur un modèle ML entraîné selon les règles officielles du **nouvel algorithme Nutri-Score (2023/2024)**.
  * Une mention visuelle explicite indique que la valeur est prédite.

#### US-02b : Calcul de l'indice de confiance
* **En tant qu'** : Utilisateur.
* **Je veux** : Voir un indice de confiance (pourcentage) associé à la fiche du produit.
* **Afin d'** : Évaluer la fiabilité des informations affichées.
* **Critères d'acceptation** :
  * L'indice varie selon le taux de complétude des variables nutritionnelles d'origine.
  * La note est visible immédiatement sur la fiche produit.

#### US-03 : Moteur de recommandation de substituts
* **En tant que** : Consommateur.
* **Je veux** : Recevoir 1 à 3 propositions d'alternatives plus saines.
* **Afin de** : Remplacer facilement un produit mal noté par un autre mieux équilibré.
* **Critères d'acceptation** :
  * Les alternatives appartiennent strictly au même sous-rayon (catégorie).
  * Les produits recommandés présentent un Nutri-Score strictement supérieur à l'original.

#### US-06b : Gestion du seuil d'incertitude ML
* **En tant qu'** : Utilisateur.
* **Je veux** : Que l'application évite d'afficher un Nutri-Score prédit si la donnée d'origine est trop pauvre.
* **Afin de** : Ne pas être induit en erreur par une prédiction risquée.
* **Critères d'acceptation** :
  * Si l'indice de confiance est inférieur à 50 %, le score prédit est masqué et remplacé par le message : *« Données insuffisantes pour estimer le score »*.

#### US-07 : Volet d'explicabilité du calcul
* **En tant qu'** : Utilisateur curieux.
* **Je veux** : Cliquer sur l'indice de confiance pour voir le détail des variables.
* **Afin de** : Découvrir quelles données sont réelles et lesquelles ont été reconstituées par l'IA.
* **Critères d'acceptation** :
  * Un volet explicatif liste distinctement les nutriments réels, manquants et imputer/estimés.

---

### Epic 3 : Core User Experience

#### US-01a : Consultation par scan de code-barres
* **En tant que** : Sophie (parent pressé).
* **Je veux** : Scanner le code-barres EAN d'un produit en rayon.
* **Afin d'** : Obtenir la fiche produit en moins de 500 ms.
* **Critères d'acceptation** :
  * Le temps de réponse backend est < 500 ms pour 95 % des requêtes.

#### US-01b : Consultation par recherche textuelle
* **En tant que** : Utilisateur.
* **Je veux** : Saisir le nom d'un produit ou d'une marque dans la barre de recherche.
* **Afin de** : Trouver une fiche sans avoir le produit physique sous la main.
* **Critères d'acceptation** :
  * Une liste de résultats pertinents est retournée lors de la saisie.

#### US-02c : Restitution pédagogique non culpabilisante
* **En tant qu'** : Utilisateur.
* **Je veux** : Lire des synthèses sur les points forts et faibles du produit rédigées clairement.
* **Afin de** : Comprendre les enjeux nutritionnels sans subir de jugement moral.
* **Critères d'acceptation** :
  * Le ton employé est strictement neutre, informatif et pédagogique.

#### US-06a : Gestion des produits hors catalogue
* **En tant que** : Utilisateur scannant un produit non référencé.
* **Je veux** : Être averti clairement par un message adapté.
* **Afin de** : Savoir que le produit n'est pas encore présent en base sans bloquer l'application.
* **Critères d'acceptation** :
  * Affichage d'un écran dédié *« Produit non répertorié »* avec option de signalement.

---

### Epic 4 : Conversational RAG

#### US-04 : Assistant Nutritionnel IA
* **En tant qu'** : Utilisateur se posant des questions sur la composition.
* **Je veux** : Poser une question en langage naturel sur la fiche du produit scanné.
* **Afin d'** : Obtenir une réponse explicative vulgarisée.
* **Critères d'acceptation** :
  * Le moteur RAG répond sous 3 secondes en se basant uniquement sur la fiche produit et les règles officielles.
  * Chaque réponse inclut la mention de non-responsabilité médicale.