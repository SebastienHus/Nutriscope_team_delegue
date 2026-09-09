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
| Direction  / Commanditaires  | Fort    | Fort    |
| Utilisateurs                 | Faible  | Fort    |
| Marketing                    | Moyen   | Fort    |
| Equipe Data                  | Faible  | Fort    |
| Equipe Projet                | Moyen   | Fort    |
| Professionnels de santé      | Faible  | Moyen   |
| Open Food Facts              | Faible  | Faible  |
| DPO / Délégué Prot. Data RGPD| Fort    | Fort    |
| Financeurs                   | Fort    | Faible  |

Postulats
- On considère ici que le **Marketing** a un pouvoir suffisamment important sur le projet. Dans les premiers mois de l'application, la priorité absolue est d'exister sur les stores et de recruter des utilisateurs. Le marketing prend le lead pour valider le positionnement, concevoir des campagnes d'acquisition agressives, travailler le référencement sur les stores et imaginer la diffusion et l'image.
- **L'équipe Data** au contraire n'a que peu d'impact. Aux prémices de l'application, la base d'utilisateurs est trop petite pour que l'équipe data puisse mener des analyses de comportement significatives ou optimiser des algorithmes de recommandation.
- Il serait pertinent de se rapprocher de **Professionnels de santé** afin de non seulement faire la promotion de l'application auprès d'eux, mais aussi pour avoir leur avis métier.

---

## 4. Personnas identifier selon objectif et besoin de l aplication 

![image](img/personae.jpg)

### Parent soucieux de l'alimentation familiale
#### Nom : Sophie Martin
#### Âge : 38 ans
#### Profession : Assistante administrative

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


### Personne diabétique et allergiques
#### Nom : Marc Leboucher
#### Âge : 57 ans
#### Profession : Comptable

Objectifs :
- Contrôler sa consommation de sucre.
- Trouver des produits alternatifs respectant ses allergies
- Identifier rapidement les produits adaptés.
- Réduire les risques liés à son alimentation.

Freins :
- Lecture complexe des tableaux nutritionnels.
- Difficulté à comparer les produits.

Situation d'usage :
Marc consulte NutriScope afin de comparer l'impact nutritionnel des produits sucrés ou trouver des alternatives à des produits sur le marché.


### Diététicienne
#### Nom : Claire Bernard
#### Âge : 31 ans
#### Profession : Diététicienne nutritionniste

Objectifs :
- Disposer d'informations fiables.
- Illustrer ses conseils auprès des patients.
- Comparer plusieurs aliments pour un bilan.

Freins :
- Informations dispersées entre plusieurs sources.

Situation d'usage :
Claire utilise NutriScope afin d'analyser les principales différences entre plusieurs produits aux apports similaires. Elle peut l'utiliser comme argument lors d'une consultation ou pour un bilan nutritionnel.

### Sportif amateur
#### Nom : Nicolas Lapoutre
#### Âge : 20 ans
#### Profession : Etudiant

Objectifs :
- Chercher à prendre de la masse musculaire.
- Contrôler ses apports nutritionnels en termes d'énergie et de protéines.
- Limiter les aliments ultra-transformés.

Freins :
- Marketing nutritionnel parfois trompeur.
- Comparaison difficile entre plusieurs marques.

Situation d'usage :
Nicolas analyse en magasin les produits protéinés et les boissons
énergétiques. Il trie ses recherches selon l'apport en protéines et en énergie.

- À détailler

### Senior surveillant sa santé
#### Nom : Jean Moreau
#### Âge : 68 ans
#### Profession : Retraité

Objectifs :
- Limiter le sel, le sucre et les graisses.
- Préserver sa santé cardiovasculaire.
- Comprendre facilement les informations nutritionnelles.

Freins :
- Applications parfois complexes.
- Terminologie nutritionnelle difficile à interpréter.

Situation d'usage :
Jean récent dans l'utilisation numérique, consulte ponctuellement NutriScope avant d'acheter un produit qu'il ne connait pas. Il voit facilement si un aliment est faible en sel, en graisse et en sucres.

# recap

==================================================
CONSOMMATEURS GRAND PUBLIC
==================================================

- Sophie Martin
  Parent soucieux de l'alimentation familiale

- Jean Moreau
  Senior attentif à sa santé

- Nicolas Lapoutre
  Sportif amateur


==================================================
PERSONNES AVEC BESOINS NUTRITIONNELS SPÉCIFIQUES
==================================================

- Marc Leboucher
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
PROFESSIONNELS DE L'AGROALIMENTAIRE (ARCHIVES)
==================================================

- Responsable Qualité

- Responsable R&D

- Responsable Réglementaire

- Chef de produit

- Responsable Innovation

- Responsable Marketing Produit


==================================================
PERSONAS LES PLUS PERTINENTS POUR LE PROJET
==================================================

1. Sophie Martin
   Parent soucieux de l'alimentation familiale

2. Marc Leboucher
   Patient diabétique et allergique

3. Nicolas Lapoutre
   Etudiant sportif amateur

4. Jean Moreau
   Senior surveillant sa santé

Couverture des besoins :
- Grand public
- Sport
- Santé / alimentation spécialisée
- Tranches d'âge étalées

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
