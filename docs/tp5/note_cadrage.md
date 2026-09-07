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

identification pouvoir / intérêt

| Partie prenante              | Pouvoir | Intérêt |
|------------------------------|---------|---------|
| Fondateurs NutriScope        | Fort    | Fort    |
| Formateurs / Commanditaires  | Fort    | Fort    |
| Référent métier nutrition    | Moyen   | Fort    |
| Responsable technique        | Moyen   | Fort    |
| Utilisateurs                 | Faible  | Fort    |
| Professionnels de santé      | Faible  | Moyen   |
| Open Food Facts              | Moyen   | Moyen   |
| DPO / RGPD                   | Moyen   | Fort    |
| Hébergeur                    | Moyen   | Faible  |
| Financeurs                   | Fort    | Moyen   |


Le DPO  peu de pouvoir opérationnel mais un fort pouvoir de blocage en cas de non-conformité.
Open Food Facts fournisseur data de base Leur intérêt tres limite si ce nest repartage selonlicence definis.
Professionnels de santé ne sont pas au cœur du périmètre puisque NutriScope n'est pas un outil médical.

point a voir 
Référent nutrition et Responsable technique peuvent etre les fondateurs (es ce les formateur pour la direction ??), donc  pouvoir est en réalité lié à celui des fondateurs.


pour nutriscope 


| Pouvoir élevé / Intérêt élevé | Pouvoir élevé / Intérêt faible |
|------------------------------|-------------------------------|
| GÉRER DE PRÈS                | MAINTENIR SATISFAIT           |
| Fondateurs NutriScope        | Financeurs                    |
| Formateurs / Commanditaires  | DPO / RGPD                    |
| Référent métier nutrition    | Hébergeur                     |
| Responsable technique        |                               |

| Pouvoir faible / Intérêt élevé | Pouvoir faible / Intérêt faible |
|-------------------------------|--------------------------------|
| MAINTENIR INFORMÉ             | SURVEILLER                     |
| Utilisateurs                  | Acteurs externes non impliqués |
| Professionnels de santé       | Concurrents                    |
| Communauté Open Food Facts    | Grand public non utilisateur   |
| Testeurs                      |                                |


analyse de matrice 

Les acteurs à gérer de près disposent d'un fort pouvoir et d'un fort intérêt
dans le projet. Ils participent directement aux décisions stratégiques,
fonctionnelles et techniques. Pour NutriScope, il s'agit principalement
des fondateurs et des commanditaires du projet.

Les acteurs à maintenir satisfaits possèdent une capacité d'influence
importante mais interviennent peu dans les activités quotidiennes.
Le DPO, les financeurs ou l'hébergeur doivent être consultés régulièrement
afin d'éviter tout blocage réglementaire, financier ou technique.

Les acteurs à maintenir informés ont un intérêt élevé mais peu de pouvoir
de décision. Les utilisateurs, les testeurs et la communauté Open Food Facts
peuvent fournir des retours précieux permettant d'améliorer le produit.

Enfin, les acteurs à surveiller disposent d'un faible niveau d'intérêt
et d'influence. Une veille périodique est suffisante afin de détecter
une éventuelle évolution de leur position vis-à-vis du projet.


---

## 4. Personnas identifier selon objectif et besoin de l aplication 


# Parent soucieux de l'alimentation familiale
Nom : Micheline Martin
Âge : 38 ans
Profession : Assistante administrative

Objectifs :
- Faire des choix alimentaires plus sains pour sa famille.
- Gagner du temps pendant les courses.
- Comparer rapidement plusieurs produits.

Freins :
- Manque de temps.
- Difficulté à comprendre les étiquettes.
- Trop d'informations contradictoires.

Situation d'usage :
Sophie utilise NutriScope dans les rayons d'un supermarché afin
de comparer plusieurs céréales pour le petit-déjeuner de ses enfants.


# Personne diabétique
Nom : Marc Leboucher
Âge : 57 ans
Profession : Comptable

Objectifs :
- Contrôler sa consommation de sucre.
- Identifier rapidement les produits adaptés.
- Réduire les risques liés à son alimentation.

Freins :
- Lecture complexe des tableaux nutritionnels.
- Difficulté à comparer les produits.

Situation d'usage :
Marc consulte NutriScope avant d'acheter des biscuits ou
desserts afin d'évaluer leur impact nutritionnel.


# Étudiant avec budget limité
Nom : Violette
Âge : 22 ans
Profession : Étudiante

Objectifs :
- Manger correctement sans augmenter son budget.
- Trouver le meilleur compromis qualité/prix.

Freins :
- Budget serré.
- Peu de connaissances en nutrition.

Situation d'usage :
Lucas compare plusieurs produits premiers prix pour
identifier celui ayant le meilleur profil nutritionnel.


# Diététicienne
Nom : Claire Bernard
Âge : 31 ans
Profession : Diététicienne nutritionniste

Objectifs :
- Disposer d'informations fiables.
- Illustrer ses conseils auprès des patients.
- Comparer rapidement plusieurs aliments.

Freins :
- Temps de consultation limité.
- Informations dispersées entre plusieurs sources.

Situation d'usage :
Claire utilise NutriScope en consultation pour expliquer
les différences entre plusieurs produits similaires.


# Sportif amateur
Nom : Nicolas Lapoutre
Âge : 29 ans
Profession : Développeur

Objectifs :
- Optimiser son alimentation.
- Contrôler ses apports nutritionnels.
- Limiter les aliments ultra-transformés.

Freins :
- Marketing nutritionnel parfois trompeur.
- Comparaison difficile entre plusieurs marques.

Situation d'usage :
Julien analyse les produits protéinés ou les boissons
énergétiques avant achat.


# Senior surveillant sa santé
Nom : Jean Moreau
Âge : 68 ans
Profession : Retraité

Objectifs :
- Limiter le sel, le sucre et les graisses.
- Préserver sa santé cardiovasculaire.
- Comprendre facilement les informations nutritionnelles.

Freins :
- Applications parfois complexes.
- Terminologie nutritionnelle difficile à interpréter.

Situation d'usage :
Jean consulte NutriScope avant ses achats alimentaires
hebdomadaires.

# recap

==================================================
CONSOMMATEURS GRAND PUBLIC
==================================================

- Sophie Martin
  Parent soucieux de l'alimentation familiale

- Lucas Dupont
  Étudiant à petit budget

- Jean Moreau
  Senior attentif à sa santé

- Julien Martin
  Sportif amateur


==================================================
PERSONNES AVEC BESOINS NUTRITIONNELS SPÉCIFIQUES
==================================================

- Marc Leroy
  Patient diabétique

- Personne souffrant d'hypertension

- Personne suivant un régime pauvre en sel

- Personne en situation de surpoids

- Personne allergique ou intolérante à certains aliments

- Patient suivi pour une maladie cardiovasculaire


==================================================
PROFESSIONNELS DE SANTÉ
==================================================

- Claire Bernard
  Diététicienne nutritionniste

- Médecin nutritionniste

- Pharmacien

- Coach nutrition

- Infirmier en éducation thérapeutique


==================================================
PROFESSIONNELS DE L'AGROALIMENTAIRE
==================================================

- Thomas Richard
  Responsable Qualité

- Responsable R&D

- Responsable Réglementaire

- Chef de produit

- Responsable Innovation

- Responsable Marketing Produit


==================================================
ACTEURS DE L'ÉCOSYSTÈME DONNÉES ALIMENTAIRES
==================================================

- Contributeur Open Food Facts

- Data Steward

- Responsable Open Data

- Analyste Données Alimentaires


==================================================
PERSONAS LES PLUS PERTINENTS POUR LE PROJET
==================================================

1. Sophie Martin
   Parent soucieux de l'alimentation familiale

2. Marc Leroy
   Patient diabétique

3. Thomas Richard
   Responsable Qualité Agroalimentaire

Couverture des besoins :
- Grand public
- Santé / alimentation spécialisée
- Industrie agroalimentaire

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

JALON J1 : Base SQL opérationnelle

--------------------------------------------------------------------------------
MOIS 2 — PIPELINE DE NETTOYAGE
--------------------------------------------------------------------------------
██████ Normalisation (tags pays, EAN, nutrition)
██████ Pipeline de nettoyage rejouable
██████ Création des indicateurs maison (nutriscore_data_complete)
██████ Segmentation des sous‑datasets
░░░░░░ Tableau de bord EDA

JALON J2 : Pipeline data validé

--------------------------------------------------------------------------------
MOIS 3 — MODÈLE NUTRI‑SCORE
--------------------------------------------------------------------------------
██████ Sélection du dataset complet
██████ Entraînement du modèle prédictif
██████ Validation croisée
██████ Analyse des biais
░░░░░░ Documentation modèle

JALON J3 : Modèle Nutri‑Score validé

--------------------------------------------------------------------------------
MOIS 4 — MOTEUR DE SUBSTITUTION
--------------------------------------------------------------------------------
██████ Définition des règles de substitution
██████ Construction du moteur IA
██████ Tests sur plusieurs rayons
░░░░░░ Ajustements + documentation

JALON J4 : Substitution opérationnelle

--------------------------------------------------------------------------------
MOIS 5 — ASSISTANT RAG
--------------------------------------------------------------------------------
██████ Construction du corpus (catalogue + sources publiques)
██████ Vectorisation / indexation
██████ Développement du chatbot RAG
██████ Tests de robustesse (hallucinations)
░░░░░░ Documentation assistant

JALON J5 : Assistant RAG validé

--------------------------------------------------------------------------------
MOIS 6 — API & DÉPLOIEMENT
--------------------------------------------------------------------------------
██████ API FastAPI exposant les modèles
██████ Conteneurisation Docker
██████ Déploiement cloud
██████ Mini‑application de démonstration
░░░░░░ Documentation technique

JALON J6 : API + déploiement opérationnels

--------------------------------------------------------------------------------
MOIS 7 — CONFORMITÉ & QUALITÉ
--------------------------------------------------------------------------------
██████ Registre RGPD
██████ Analyse de biais (consolidation)
██████ Positionnement AI Act
██████ Accessibilité RGAA
░░░░░░ Documentation conformité

JALON J7 : Conformité validée

--------------------------------------------------------------------------------
MOIS 8 — DOSSIER FINAL & SOUTENANCE
--------------------------------------------------------------------------------
██████ Rédaction dossier final
██████ Préparation soutenance
██████ Tests finaux de l’application
░░░░░░ Corrections / stabilisation

LIVRABLE FINAL : Application IA NutriScope + dossier complet

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
