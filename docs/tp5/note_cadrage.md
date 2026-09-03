================================================================================
                     NOTE DE CADRAGE — PROJET IA NUTRISCOPE
================================================================================

## 1. CONTEXTE DU PROJET NUTRISCOPE 
NutriScope est un projet d’application d’intelligence artificielle destinée au grand public, dont l’objectif est d’aider les consommateurs à mieux choisir leurs produits alimentaires en magasin. Le projet s’inscrit dans un contexte où la transparence nutritionnelle reste limitée, les étiquettes difficiles à interpréter, et les alternatives plus saines rarement identifiables rapidement.

L’application vise un public large (utilisateurs finaux en magasin ) recherchant une solution simple, fiable et immédiate pour comprendre la qualité nutritionnelle d’un produit et identifier une substitution plus saine lorsque cela est pertinent.

NutriScope n’a pas vocation à éduquer les consommateurs ni à fournir des conseils médicaux. Il ne s’agit pas d’un outil de santé, mais d’un assistant d’aide au choix, centré sur l’information nutritionnelle et la substitution. L’ambition est de proposer une expérience fluide : on scanne un produit, l’application indique son niveau de qualité nutritionnelle et suggère des alternatives plus adaptées.


### Problème
- Manque de transparence nutritionnelle.
- Difficulté à comprendre les étiquettes.
- Absence d’outils simples pour comparer ou substituer un produit.

### Opportunités
- IA pour guider les choix alimentaires.
- Chatbot RAG pour répondre aux questions.
- Intégration de computer vision (lecture d’étiquettes / photos produits).

### Enjeux
- **Techniques** : qualité data, fiabilité des modèles, industrialisation.  
- **Usage** : mieux manger, substitution.  
- **Conformité** : RGPD, AI Act, RGAA.

---

## 2. OBJECTIFS DU PROJET (SMART)
- Construire une base produits propre et exploitable.  
- Développer un modèle de prédiction du Nutri-Score.  
- Créer un moteur de substitution.  
- Entraîner un classifieur d’images *(à confirmer selon faisabilité)*.  
- Développer un assistant RAG.  
- Déployer une API et une mini-application.  
- Livrer conformité RGPD / AI Act.

---

## 3. PÉRIMÈTRE FONCTIONNEL

### Inclus
- 5 à 8 rayons alimentaires.  
- Pipeline de nettoyage.  
- Modèles IA (Nutri-Score, substitution).  
- Assistant RAG.  
- API FastAPI + démonstrateur.  
- Conformité RGPD / AI Act.

### Pistes d’amélioration (hors périmètre)
- Application mobile complète.  
- Interface utilisateur avancée.  
- Recommandations personnalisées (profil utilisateur).  

---

## 4. PARTIES PRENANTES & RÔLES
- **Direction NutriScope (formateurs)** : commanditaire, validation des jalons.  
- **Équipe IA (nous)** : réalisation du projet.  
- **Formateurs** : rôle de direction, arbitrage.  
- **Utilisateurs finaux** : consommateurs en magasin.

---

## 5. PLANNING PRÉVISIONNEL — PROJET NUTRISCOPE

Légende :
██████  Phase principale
░░░░░░  Travail complémentaire / consolidation

--------------------------------------------------------------------------------
MOIS 1 — SOCLE DATA & BASE SQL
--------------------------------------------------------------------------------
██████ Profiling complet (distributions, manquants, incohérences)
██████ Définition du périmètre data (rayons, colonnes, seuils)
██████ Modélisation relationnelle (3FN)
██████ Construction du dataset maître
░░░░░░ Documentation périmètre + EDA

🎯 JALON J1 : Base SQL opérationnelle

--------------------------------------------------------------------------------
MOIS 2 — PIPELINE DE NETTOYAGE
--------------------------------------------------------------------------------
██████ Normalisation (tags pays, EAN, nutrition)
██████ Pipeline de nettoyage rejouable
██████ Création des indicateurs maison (nutriscore_data_complete)
██████ Segmentation des sous‑datasets
░░░░░░ Tableau de bord EDA

🎯 JALON J2 : Pipeline data validé

--------------------------------------------------------------------------------
MOIS 3 — MODÈLE NUTRI‑SCORE
--------------------------------------------------------------------------------
██████ Sélection du dataset complet
██████ Entraînement du modèle prédictif
██████ Validation croisée
██████ Analyse des biais
░░░░░░ Documentation modèle

🎯 JALON J3 : Modèle Nutri‑Score validé

--------------------------------------------------------------------------------
MOIS 4 — MOTEUR DE SUBSTITUTION
--------------------------------------------------------------------------------
██████ Définition des règles de substitution
██████ Construction du moteur IA
██████ Tests sur plusieurs rayons
░░░░░░ Ajustements + documentation

🎯 JALON J4 : Substitution opérationnelle

--------------------------------------------------------------------------------
MOIS 5 — ASSISTANT RAG
--------------------------------------------------------------------------------
██████ Construction du corpus (catalogue + sources publiques)
██████ Vectorisation / indexation
██████ Développement du chatbot RAG
██████ Tests de robustesse (hallucinations)
░░░░░░ Documentation assistant

🎯 JALON J5 : Assistant RAG validé

--------------------------------------------------------------------------------
MOIS 6 — API & DÉPLOIEMENT
--------------------------------------------------------------------------------
██████ API FastAPI exposant les modèles
██████ Conteneurisation Docker
██████ Déploiement cloud
██████ Mini‑application de démonstration
░░░░░░ Documentation technique

🎯 JALON J6 : API + déploiement opérationnels

--------------------------------------------------------------------------------
MOIS 7 — CONFORMITÉ & QUALITÉ
--------------------------------------------------------------------------------
██████ Registre RGPD
██████ Analyse de biais (consolidation)
██████ Positionnement AI Act
██████ Accessibilité RGAA
░░░░░░ Documentation conformité

🎯 JALON J7 : Conformité validée

--------------------------------------------------------------------------------
MOIS 8 — DOSSIER FINAL & SOUTENANCE
--------------------------------------------------------------------------------
██████ Rédaction dossier final
██████ Préparation soutenance
██████ Tests finaux de l’application
░░░░░░ Corrections / stabilisation

🎯 LIVRABLE FINAL : Application IA NutriScope + dossier complet
================================================================================


---

## 6. CONTRAINTES IDENTIFIEES

### Techniques
- Qualité data, performance des modèles.  
- Outils imposés :  
  - Python 3.12  
  - Git (dépôt d’équipe)  
  - DuckDB / PostgreSQL  
  - scikit-learn  
  - TensorFlow / Keras  
  - FastAPI  
  - Docker  
- Code et variables en anglais.  
- Documentation et soutenances en français.

### Organisationnelles
- Travail en équipe, agilité.

### Réglementaires
- RGPD  
- AI Act  
- RGAA (accessibilité)

### Temps
- 216 heures de projet fil rouge.

---

## 7. RISQUES & PARADES
- **Data incomplète** → seuil de complétude.  
- **Modèles instables** → validation croisée.  
- **Charge de travail** → découpage clair.  
- **Biais nutritionnels** → analyse dédiée.  
- **Conformité IA** → documentation continue.  
- **Compréhension des attentes utilisateurs** → étude de marché.

---

## 11. SYNTHÈSE
Cette note de cadrage fixe le périmètre, les objectifs, les contraintes et les livrables du projet NutriScope.  
Elle constitue la référence stratégique pour les 8 mois de développement du fil rouge.

Le projet vise à produire une application IA fiable, conforme, industrialisée, et utile pour les consommateurs dans leurs choix alimentaires.

================================================================================
FIN DU DOCUMENT
================================================================================
