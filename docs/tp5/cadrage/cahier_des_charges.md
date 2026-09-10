# Cahier des Charges — Projet IA NutriScope

## 1. Contexte et objectifs

### 1.1 Contexte du projet
Le projet NutriScope est une application d'aide à la décision alimentaire destinée au grand public. En magasin, les consommateurs — représentés par le persona principal **Sophie Martin** (parent pressé gérant les courses du foyer) — font face à une forte fatigue informationnelle. Les étiquettes nutritionnelles restent complexes, les données sont dispersées et la comparaison de produits est chronophage (plus d'une minute par produit aujourd'hui).

L'application cible en premier lieu les produits distribués sur le marché français, tout en exploitant la richesse du catalogue mondial Open Food Facts. NutriScope automatise l'analyse et l'explication nutritionnelle grâce à l'IA (processus TO-BE) pour réduire le temps de décision en rayon à **moins de 30 secondes**. Le positionnement est informatif, pédagogique et non culpabilisant, sans prétention médicale.

### 1.2 Objectifs SMART
Pour encadrer le développement et le déploiement du projet NutriScope, les objectifs sont structurés selon la méthode SMART (faisant foi pour le calendrier du projet) :

* **Spécifique** : Concevoir et déployer une application d'aide au choix alimentaire intégrant un pipeline de nettoyage data rejouable, un modèle prédictif de Nutri-Score basé sur le nouvel algorithme officiel, un moteur de substitution de produits et un assistant conversationnel RAG vulgarisant la composition nutritionnelle. L'application garantit une explicabilité complète et affiche un indice de confiance sur la fiabilité des données source.
* **Mesurable** : 
  * Atteindre une note moyenne supérieure à **4.3/5** sur les stores applicatifs.
  * Capter **231 000 MAU au Mois 6** et **3 400 000 MAU à 36 mois**.
  * Obtenir un taux de réutilisation (fidélisation) de l'application de **40 %**.
  * Réduire le temps de comparaison en rayon de **60 s à 30 s** par session.
* **Atteignable** : Exploitation du jeu de données filtré et qualifié d'Open Food Facts, adossé à une stack technique éprouvée (Python 3.12, DuckDB, scikit-learn, FastAPI, Docker).
* **Réaliste** : Alignement strict sur les contraintes RGPD (minimisation des données, consentement, absence de revente nominative) et cadrage éthique évitant tout conseil médical.
* **Temporellement défini** : 
  * Version pilote / MVP livrée sous **3 mois**.
  * Version publique finale et déploiement initial sous **4 mois**.
  * Déploiement global et passage à l'échelle consolidés sous **6 mois**.

---

## 2. Périmètre

### 2.1 Conclusions d'exploration Data & Périmètre
La définition du périmètre NutriScope s'appuie directement sur les travaux d'analyse exploratoire et de cadrage de données réalisés à partir de la base ouverte Open Food Facts :

* **Périmètre géographique et volumétrie :** Exploitation globale de la base de données internationale sans restriction géographique initiale (~4 millions de produits). L'application s'adresse en priorité aux consommateurs du marché français tout en restant capable de traiter les références mondiales.
* **Critères d'inclusion data :** Un produit est retenu en base s'il possède un code-barres valide, une dénomination (`product_name`) et s'il respecte le seuil de complétude sur les nutriments clés (`energy_100g`, `sugars_100g`, `salt_100g`).
* **Format d'ingestion et rafraîchissement :** Le modèle et les moteurs s'appuient sur un *snapshot* qualifié de la base Open Food Facts pour les phases d'entraînement et de cadrage, avec un pipeline permettant d'injecter périodiquement les nouvelles données du flux OFF.
* **Traitements de nettoyage :** Élimination systématique des doublons de codes-barres et exclusion des valeurs physiquement impossibles ou aberrantes (ex. taux de sucre supérieur à 100g, valeurs énergétiques négatives).
* **Segmentation fonctionnelle :** Restriction prioritaire du catalogue aux **5 à 8 rayons alimentaires principaux** de la grande distribution au lancement afin d'assurer la précision et la pertinence de l'algorithme de substitution.

---

### 2.2 Tableau de priorisation et matrice du périmètre

| Composante / Fonctionnalité | Statut & Priorité | Périmètre (Inclus / Exclus) | Document de référence |
| :--- | :--- | :--- | :--- |
| **Périmètre Data Global (Open Food Facts)** | 🟢 **Inclus (MVP)** | Catalogue international complet (~4 millions de produits) nettoyé et qualifié | Note de cadrage & Étude Data |
| **Rayons alimentaires cibles** | 🟢 **Inclus (MVP)** | Restreint aux 5 à 8 rayons majeurs de la grande distribution | Note de cadrage |
| **Pipeline de nettoyage rejouable** | 🟢 **Inclus (MVP)** | Filtres de complétude & correction automatisée des incohérences | Spécifications Données |
| **Scan Code-barres (EAN) & Recherche** | 🟢 **Inclus (MVP)** | Identification produit instantanée via API REST FastAPI | Cartographie des Processus |
| **Fiche produit synthétique & Explicabilité** | 🟢 **Inclus (MVP)** | Analyse nutritionnelle vulgarisée, transparente et non culpabilisant | Cartographie & Benchmark |
| **Modèle prédictif Nutri-Score (Nouveau calcul)**| 🟢 **Inclus (MVP)** | Algorithme IA comblant l'absence de Nutri-Score selon la mise à jour 2023/2024 | Note de cadrage & Étude Data |
| **Moteur IA de Substitution** | 🟢 **Inclus (MVP)** | Recherche de produits comparables plus sains par calcul de distance vectorielle | Étude de Faisabilité |
| **Assistant Conversationnel RAG** | 🟢 **Inclus (MVP)** | Vulgarisation interactive des données nutritionnelles et réponses guidées | Étude de Faisabilité & Benchmark |
| **Indice de confiance des données** | 🟢 **Inclus (MVP)** | Affichage explicite du niveau de fiabilité de l'analyse (Transparence totale) | Benchmark Concurrentiel |
| **Historique des scans & Favoris** | 🟠 **Évolution (V2)** | Sauvegarde locale des produits et personnalisation progressive des parcours | Cartographie des Processus |
| **Profil utilisateur & Filtres allergènes** | 🟠 **Évolution (V2)** | Personnalisation selon contraintes de santé (diabète, régimes spécifiques) | Spécifications Données |
| **Reconnaissance visuelle / Photo étiquette**| 🔴 **Hors périmètre (V3)**| OCR d'étiquette et traitement par Computer Vision direct en rayon | Note de cadrage |
| **Application Mobile native dédiée** | 🔴 **Hors périmètre (MVP)**| Déploiement initial sous forme d'API FastAPI conteneurisée et démonstrateur Web | Note de cadrage |

---

## 3. Exigences fonctionnelles

### 3.1 Vue d'ensemble du Backlog (MoSCoW)

* **Must have (Indispensables pour le MVP)** : 
  * Pipeline automatisé d'ingestion et de nettoyage du catalogue mondial Open Food Facts.
  * Scan de code-barres (EAN) et recherche textuelle instantanée.
  * Fiche produit synthétique avec Nutri-Score (réel ou prédit par l'IA selon l'algorithme 2023/2024) et indice de confiance.
  * Moteur IA de substitution recommandant des alternatives plus saines dans le même rayon.
  * Assistant conversationnel RAG vulgarisant les données nutritionnelles.
  * Traitement des cas d'erreur et gestion des incertitudes de données.
* **Should have (Fortement recommandés pour V2)** : 
  * Historique local des scans et gestion des favoris.
  * Profil utilisateur avec filtres d'allergènes et contraintes alimentaires basiques.
* **Could have (Envisageables pour V3)** : 
  * Personnalisation avancée des recommandations selon les objectifs nutritionnels du foyer.
  * Personnalisation sur ordre de préférences des produits affichés.
* **Won't have (Exclus du MVP)** : 
  * Reconnaissance visuelle d'étiquettes par photo (OCR / Computer Vision).

---

### 3.2 Tableau récapitulatif des exigences du MVP

| Exigence fonctionnelle MVP | Composante IA / Data associée | Référence US |
| :--- | :--- | :--- |
| **Ingestion & Nettoyage Data** | Pipeline Python / DuckDB rejouable | **US-05** |
| **Scan EAN & Recherche** | API REST FastAPI | **US-01** |
| **Nutri-Score prédit & Transparence** | Modèle Scikit-learn (Mise à jour 2023/2024) & Indice de confiance | **US-02** |
| **Explicabilité de l'indice de confiance** | Algorithme d'audit des features manquantes/estimées | **US-07** |
| **Recommandation d'alternatives** | Moteur de substitution (distance vectorielle) | **US-03** |
| **Assistant Nutritionnel** | Moteur conversationnel RAG | **US-04** |
| **Gestion des erreurs & Incertitudes** | Gestionnaire d'incertitude (< 50 % de confiance) | **US-06** |

---

### 3.3 Spécification des User Stories

#### US-01a : Scan et recherche de produit
* **En tant que** : Sophie (parent pressé).
* **Je veux** : Scanner le code-barres d'un produit en magasin.
* **Afin de** : Accéder instantanément à sa fiche d'analyse nutritionnelle sans perdre de temps en rayon.
* **Critères d'acceptation** :
  * Le temps de réponse de l'API pour retourner la fiche produit doit être inférieur à 500 ms.
  * Si le code-barres est absent du catalogue, un message clair informe l'utilisateur sans provoquer d'erreur critique.

#### US-01b : Scan et recherche de produit
* **En tant que** : Sophie (parent pressé).
* **Je veux** : Scanner le code-barres d'un produit en magasin ou saisir son nom dans la barre de recherche.
* **Afin de** : Accéder instantanément à sa fiche d'analyse nutritionnelle sans perdre de temps en rayon.
* **Critères d'acceptation** :
  * Le temps de réponse de l'API pour retourner la fiche produit doit être inférieur à 500 ms.
  * Si le code-barres est absent du catalogue, un message clair informe l'utilisateur sans provoquer d'erreur critique.

#### US-02 : Transparence et Nutri-Score prédit
* **En tant qu'** : Utilisateur soucieux de sa santé.
* **Je veux** : Voir la fiche nutritionnelle simplifiée du produit et connaître son Nutri-Score (réel ou prédit par l'IA selon le nouvel algorithme).
* **Afin de** : Comprendre rapidement la qualité du produit, même si l'étiquette d'origine est incomplète.
* **Critères d'acceptation** :
  * Si le Nutri-Score d'origine est manquant, la valeur prédite par le modèle ML (aligné sur l'algorithme Nutri-Score 2023/2024) est affichée avec une mention explicite.
  * Un **indice de confiance** est affiché systématiquement pour garantir une transparence totale sur la fiabilité des données.
  * L'explication des points forts et faibles du produit est rédigée dans un langage pédagogique et non culpabilisant.

#### US-03 : Recommandation d'alternatives (Substitution)
* **En tant que** : Consommateur cherchant de meilleurs choix.
* **Je veux** : Obtenir 1 à 3 propositions d'alternatives plus saines équivalentes dans le même rayon.
* **Afin de** : Remplacer facilement un produit mal noté par un autre mieux équilibré.
* **Critères d'acceptation** :
  * Les alternatives suggérées appartiennent strictly à la même catégorie ou sous-catégorie de produit.
  * Les produits recommandés présentent un Nutri-Score strictement meilleur que le produit scanné.

#### US-04 : Assistant Nutritionnel (RAG Conversationnel)
* **En tant qu'** : Utilisateur se posant des questions sur la composition.
* **Je veux** : Poser une question en langage naturel sur le produit scanné (ex. « Est-ce adapté pour le goûter des enfants ? »).
* **Afin d'** : Obtenir une réponse synthétique, vérifiée et facile à comprendre.
* **Critères d'acceptation** :
  * L'assistant s'appuie uniquement sur des données factuelles et vérifiées (mode RAG sans hallucination).
  * Les réponses intègrent une clause de non-responsabilité rappelant l'absence de conseil médical direct.

#### US-05 : Pipeline automatisé d'ingestion et de nettoyage
* **En tant que** : Lead Data Engineer.
* **Je veux** : Exécuter un pipeline de nettoyage rejouable sur le snapshot du dataset Open Food Facts.
* **Afin de** : Filtrer les doublons, éliminer les valeurs aberrantes (ex. sucre > 100g) et structurer la base d'analyse.
* **Critères d'acceptation** :
  * Le script d'ingestion s'exécute de manière automatisée.
  * Les données corrompues ou invalides sont isolées et loggées dans un rapport d'audit.

#### US-06 : Gestion des produits inconnus et incertitudes
* **En tant qu'** : Utilisateur scannant un produit non répertorié ou très incomplet.
* **Je veux** : Être informé clairement si le produit est inconnu ou si l'indice de confiance est trop faible pour prédire le score.
* **Afin de** : Ne pas recevoir d'informations erronées ou de prédictions trompeuses.
* **Critères d'acceptation** :
  * Si l'indice de confiance du modèle est inférieur à 50 %, l'application affiche la mention « Données insuffisantes pour estimer le score » au lieu d'une prédiction incertaine.
  * L'utilisateur a la possibilité de signaler un produit manquant ou une incohérence.

#### US-07 : Détail explicatif de l'indice de transparence
* **En tant qu'** : Utilisateur souhaitant vérifier l'origine d'un résultat.
* **Je veux** : Consulter le détail du calcul en cliquant sur l'indice de confiance.
* **Afin de** : Comprendre quelles données ont servi au calcul (nutriments réels vs valeurs estimées par le modèle).
* **Critères d'acceptation** :
  * Un volet explicatif liste clairement les nutriments renseignés, manquants et reconstitués par le modèle IA.

---

## 4. Architecture technique, Stack & Composants IA

### 4.1 Stack technologique

* **Langage principal** : Python 3.12 (écosystème Data & IA).
* **Moteur de stockage & Ingestion Data** : DuckDB (traitement in-memory ultra-rapide des 4M+ de lignes) / SQLite pour le stockage local. ( A VALIDER )
* **Backend & API REST** : FastAPI (performances élevées, validation Pydantic, documentation Swagger automatique).
* **Framework ML & Data Processing** : Scikit-learn, Pandas, NumPy.
* **Composants RAG & NLP** : LangChain / LlamaIndex, embeddings Hugging Face, LLM open-source quantifié ou API externe. ( A VALIDER )
* **Conteneurisation & Déploiement** : Docker, Docker Compose.
* **Gestion de version & CI/CD** : GitHub / GitLab, GitHub Actions.

---

### 4.2 Architecture globale et flux de données

```
┌────────────────────────────────────────────────────────────────────────┐
│                         INTERFACE UTILISATEUR                         │
│                    (Démonstrateur Web / API)                          │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
                     HTTP / REST (EAN, Requête)
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            BACKEND FASTAPI                            │
│                                                                        │
│  ┌───────────────────────┐        ┌───────────────────────┐           │
│  │   Routeur Recherche   │        │ Routeur Substitution │           │
│  └───────────┬───────────┘        └───────────┬───────────┘           │
└──────────────┼────────────────────────────────┼───────────────────────┘
               │                                │
               ▼                                ▼

┌──────────────────────────────┐   ┌──────────────────────────────┐
│ Brique 1 : Pipeline Data     │   │ Brique 3 : Moteur de         │
│ & Nettoyage (DuckDB)         │   │ Substitution (KNN)           │
└──────────────┬───────────────┘   └──────────────┬───────────────┘
               │                                  │
               ▼                                  ▼

┌──────────────────────────────┐   ┌──────────────────────────────┐
│ Brique 2 : Modèle Prédictif  │   │ Brique 4 : Assistant RAG     │
│ Nutri-Score (Scikit-Learn)   │   │ (LangChain / Vector DB)      │
└──────────────────────────────┘   └──────────────────────────────┘
```

---

### 4.3 Description des 4 briques IA

#### Brique 1 : Ingestion, filtrage et nettoyage automatisé
* **Rôle** : Ingestion d'un snapshot du catalogue mondial Open Food Facts, filtrage des incohérences et mise à disposition d'une base propre rejouable.
* **Fonctionnement** : Application de règles métiers (suppression des doublons d'EAN, éviction des nutriments > 100g ou < 0) et gestion des mises à jour périodiques.

#### Brique 2 : Modèle prédictif du Nutri-Score & Indice de confiance
* **Rôle** : Estimation de la classe Nutri-Score (A à E) pour les fiches produits incomplètes (~55 % de la base).
* **Fonctionnement** : Algorithme de classification entraîné selon le **nouvel algorithme officiel Nutri-Score (2023/2024)** sur les variables nutritionnelles complètes. Le modèle restitue la classe estimée ainsi qu'un **indice de confiance** basés sur la qualité des features disponibles.

#### Brique 3 : Moteur de substitution de produits
* **Rôle** : Proposer 1 à 3 produits alternatifs plus sains lors d'un scan.
* **Fonctionnement** : Algorithme de recherche par plus proches voisins (K-Nearest Neighbors / distance vectorielle) restreint au même sous-rayon. Il sélectionne les références ayant un profil nutritionnel et un Nutri-Score strictement supérieurs.

#### Brique 4 : Assistant conversationnel RAG (Retrieval-Augmented Generation)
* **Rôle** : Répondre aux questions en langage naturel des utilisateurs sur la composition des produits de manière transparente et vulgarisée.
* **Fonctionnement** : Vectorisation des fiches produits et des règles nutritionnelles. Le LLM génère une réponse basée sur le contexte extrait, garantissant l'absence d'hallucinations.

---

## 5. Exigences non fonctionnelles, Sécurité & Éthique

### 5.1 Performance et Sécurité

* **Temps de réponse (Latence)** :
  * Recherche et consultation de fiche produit : temps de réponse de l'API inférieur à **500 ms** pour 95 % des requêtes.
  * Moteur de substitution : génération des alternatives en moins de **1 seconde**.
  * Assistant RAG : génération de la réponse conversationnelle sous **3 secondes**.
* **Disponibilité et Scalabilité** :
  * Architecture conteneurisée (Docker) dimensionnée pour supporter la montée en charge progressive (jusqu'à 3,4 M MAU à 36 mois).
  * Taux de disponibilité cible de l'API de **99,5 %**.
* **Traçabilité et Logging** :
  * Journalisation complète des exécutions du pipeline d'ingestion pour tracer les rejets de données corrompues.
  * Versioning explicite des modèles ML et des données.

---

### 5.2 Protection des données (RGPD) et Confidentialité

* **Minimisation des données** : 
  * Le MVP fonctionne sans création de compte obligatoire ni collecte d'informations personnelles nominatives.
  * Les requêtes de scan ou de recherche ne stockent aucune donnée directement identifiante sur les serveurs backend.
* **Sécurité des échanges** :
  * Encadrement strict des flux d'API REST via le protocole HTTPS / TLS.
* **Valorisation et anonymisation des données** :
  * Aucune donnée nominative ou individuelle n'est commercialisée.
  * Seules des données d'usage totalement anonymisées et agrégées à l'échelle macro pourront faire l'objet d'une valorisation B2B (insights de marché), dans le respect strict du RGPD.

---

### 5.3 Cadrage Éthique, Transparence et Responsabilité

* **Transparence et explicabilité complète** :
  * **Affichage de l'indice de confiance** : chaque résultat prédit est accompagné d'un score de fiabilité.
  * **Explicabilité des calculs** : accès en un clic au détail des nutriments réellement renseignés versus ceux estimés par le modèle IA (calculé selon l'algorithme Nutri-Score 2023/2024).
* **Positionnement neutre et non culpabilisant** :
  * Restitution des informations dans un ton neutre, clair et accessible.
* **Absence de conseil médical** :
  * L'application conserve un rôle strict d'aide à la décision.
  * Intégration systématique d'une mention légale rappelant que NutriScope ne dispense aucun diagnostic ni prescription médicale.

---

## 6. Planning, Livrables & Rituels

### 6.1 Planning et Jalons clés

Le calendrier s'aligne sur les engagements SMART pour livrer la version pilote MVP à 3 mois, la version publique à 4 mois, et consolider l'industrialisation sous 6 mois.

| Jalon | Intitulé du Jalon | Période | Livrables associés |
| :--- | :--- | :--- | :--- |
| **J1** | Explorations Data & Cadrage | Mois 1 | Rapport d'exploration (EDA), filtres, note de cadrage initial |
| **J2** | Faisabilité & Clean Pipeline | Mois 2 | Étude de faisabilité des briques IA, scripts de nettoyage Python/DuckDB |
| **J3** | **Livraison Pilote / MVP** | **Mois 3** | **Pipeline Data, Modèle Nutri-Score (nouveau calcul), API REST & Démonstrateur Web** |
| **J4** | **Lancement Version Publique (v1.0)** | **Mois 4** | **Moteur de substitution, assistant RAG intégré, déploiement public** |
| **J5** | Tests de charge & Optimisations | Mois 5 | Tests d'intégration, optimisation latence (< 500ms), conteneurisation finale |
| **J6** | Passage à l'échelle (231k MAU) | Mois 6 | Recette finale, Tag v0.2 / v1.5, documentation d'architecture consolidée |

---

### 6.2 Livrables clés du projet

* **Code source & Repository Git** :
  * Repository structuré (GitHub / GitLab) avec gestion de version et étiquetage (Tag v0.2 / v1.0).
  * Scripts Python modulaires (ingestion, prédiction, API).
* **Documentation technique & Métier** :
  * Cahier des charges fonctionnel et technique validé.
  * Cartographie complète des processus (AS-IS et TO-BE).
  * Documentation d'architecture et de déploiement (Dockerfile, Docker Compose).
  * Swagger / OpenAPI interactif généré automatiquement par FastAPI.
* **Composants IA & Artefacts** :
  * Modèle de classification du Nutri-Score aligné 2023/2024 (fichiers `.pkl` / `.joblib`).
  * Index vectoriel pour le moteur de substitution et l'assistant RAG.

---

### 6.3 Rituels d'équipe et Outillage

L'équipe projet fonctionne selon une méthodologie **Agile / Scrum simplifiée** :

* **Rituels d'équipe** :
  * **Sprint Planning** (bimensuel) : Définition des objectifs et engagement sur le backlog.
  * **Stand-up meeting** (2 à 3 fois par semaine) : Point synchrone de 15 minutes pour lever les verrous techniques.
  * **Sprint Review & Rétrospective** (en fin de jalon) : Démonstration et amélioration continue.
* **Environnement de travail et Outillage** :
  * **Gestion de code et CI/CD** : GitHub / GitLab (branches, PR, tags).
  * **Suivi des tâches & Backlog** : Board Kanban dédié (méthode MoSCoW).
  * **Conteneurisation** : Docker pour garantir l'homogénéité des environnements.