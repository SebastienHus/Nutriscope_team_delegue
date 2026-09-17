# Cahier des Charges — Projet IA NutriScope

## 1. Contexte et objectifs

### 1.1 Contexte du projet
Le projet NutriScope est une application d'aide à la décision alimentaire destinée au grand public. En magasin, les consommateurs — représentés par le persona principal **Sophie Martin** (parent pressé gérant les courses du foyer) — font face à une forte fatigue informationnelle. Les étiquettes nutritionnelles restent complexes, les données sont dispersées et la comparaison de produits est chronophage (plus d'une minute par produit aujourd'hui).

L'application cible en premier lieu les produits distribués sur le marché français, tout en exploitant la richesse du catalogue mondial Open Food Facts. NutriScope automatise l'analyse et l'explication nutritionnelle grâce à l'IA (processus TO-BE) pour réduire le temps de décision en rayon à **moins de 30 secondes**. Le positionnement est informatif, pédagogique et non culpabilisant, sans prétention médicale.

### 1.2 Objectifs SMART
Pour encadrer le développement et le déploiement du projet NutriScope, les objectifs sont structurés selon la méthode SMART :

* **Spécifique** : Concevoir et déployer une application d'aide au choix alimentaire intégrant un pipeline de nettoyage data rejouable, un modèle prédictif de Nutri-Score basé sur le nouvel algorithme officiel, un moteur de substitution de produits et un assistant conversationnel RAG vulgarisant la composition nutritionnelle.
* **Mesurable** : Atteindre une note moyenne supérieure à 4.3/5 sur les stores applicatifs, 231 000 MAU au Mois 6, un taux de réutilisation de 40 %, réduire le temps de comparaison de 60s à 30s.
* **Atteignable** : Exploitation du jeu de données d'Open Food Facts avec stack Python 3.12, DuckDB, scikit-learn, FastAPI, Docker.
* **Réaliste** : Alignement strict sur les contraintes RGPD et cadrage éthique.
* **Temporellement défini** : MVP à 3 mois, v1.0 à 4 mois, déploiement global à 6 mois.

---

## 2. Périmètre

### 2.1 Conclusions d'exploration Data & Périmètre
La définition du périmètre NutriScope s'appuie directement sur les travaux d'analyse exploratoire et de cadrage de données réalisés à partir d'Open Food Facts :

* **Périmètre géographique** : Exploitation globale de la base (~4 millions de produits), priorité au marché français.
* **Critères d'inclusion data** : Produits avec code-barres valide, dénomination, et seuil minimum de complétude nutritionnelle.
* **Traitements de nettoyage** : Élimination des doublons et valeurs aberrantes.
* **Segmentation fonctionnelle** : Restriction à 5-8 rayons alimentaires au lancement.

---

## 3. Exigences fonctionnelles

### 3.1 Must have (MVP)
- Pipeline automatisé d'ingestion et nettoyage
- Scan de code-barres et recherche instantanée
- Fiche produit avec Nutri-Score et indice de confiance
- Moteur IA de substitution
- Assistant conversationnel RAG
- Traitement des cas d'erreur et incertitudes

### 3.2 User Stories principales

#### US-01 : Scan et recherche de produit
Scanner le code-barres ou rechercher par nom pour accéder instantanément à la fiche d'analyse nutritionnelle sans perdre de temps en rayon. Temps de réponse < 500 ms.

#### US-02 : Transparence et Nutri-Score prédit
Voir la fiche nutritionnelle simplifiée avec Nutri-Score réel ou prédit par l'IA, accompagné d'un indice de confiance explicite.

#### US-03 : Recommandation d'alternatives
Obtenir 1 à 3 propositions d'alternatives plus saines dans la même catégorie de produit.

#### US-04 : Assistant Nutritionnel (RAG)
Poser une question en langage naturel sur la composition et obtenir une réponse synthétique, vérifiée et facile à comprendre.

#### US-05 : Pipeline automatisé
Exécuter un pipeline de nettoyage rejouable sur le dataset Open Food Facts avec isolation des données corrompues.

#### US-06 : Gestion des incertitudes
Être informé clairement si le produit est inconnu ou si l'indice de confiance est insuffisant (< 50 %).

#### US-07 : Détail explicatif
Consulter le détail du calcul de l'indice de confiance et comprendre quelles données ont été renseignées vs estimées.

---

## 4. Architecture technique

### Stack technologique
- **Langage** : Python 3.12
- **Moteur de stockage** : DuckDB / SQLite
- **Backend API** : FastAPI
- **Framework ML** : Scikit-learn, Pandas, NumPy
- **RAG & NLP** : LangChain / LlamaIndex, embeddings Hugging Face
- **Conteneurisation** : Docker, Docker Compose
- **CI/CD** : GitHub, GitHub Actions

### 4 Briques IA
1. **Ingestion & Nettoyage** : Pipeline de qualité data
2. **Modèle Nutri-Score** : Classification selon algorithme 2023/2024 + indice de confiance
3. **Moteur de Substitution** : KNN pour alternatives dans même catégorie
4. **Assistant RAG** : Vulgarisation conversationnelle sans hallucinations

---

## 5. Exigences non fonctionnelles

### Performance
- Latence recherche/fiche produit : < 500 ms (95 percentile)
- Substitution : < 1 seconde
- Assistant RAG : < 3 secondes
- Disponibilité API : 99,5 %

### Sécurité & Données (RGPD)
- Minimisation des données nominatives
- Aucune revente de données identifiantes
- Seules données anonymisées et agrégées pour B2B
- Transparence complète avec indice de confiance

### Éthique & Transparence
- Affichage obligatoire de l'indice de confiance
- Explicabilité complète des calculs
- Ton neutre, pédagogique, non culpabilisant
- Mention légale : outil informatif, non médical

---

## 6. Planning et Livrables

| Jalon | Intitulé | Période | Livrables |
| :--- | :--- | :--- | :--- |
| **J1** | Explorations Data | Mois 1 | Rapport EDA, filtres, note de cadrage |
| **J2** | Faisabilité & Clean Pipeline | Mois 2 | Étude de faisabilité, scripts Python/DuckDB |
| **J3** | MVP Pilote | Mois 3 | Pipeline Data, Modèle Nutri-Score, API REST |
| **J4** | v1.0 Publique | Mois 4 | Substitution, Assistant RAG, déploiement |
| **J5** | Tests & Optimisations | Mois 5 | Tests d'intégration, latence < 500ms |
| **J6** | Passage à l'échelle | Mois 6 | Recette finale, v0.2/v1.5, documentation |

---

## Conclusion

Ce cahier des charges fixe le périmètre fonctionnel et technique du projet NutriScope, aligné avec les objectifs SMART et les livrables du planning prévisionnel. Il constitue la référence pour le développement des 8 mois de projet fil rouge.
