# 📑 DOCUMENT DE SYNTHÈSE STRATÉGIQUE & FINANCIÈRE : PROJET IA NUTRISCOPE

**Date de mise à jour :** Septembre 2026  
**Statut :** Cadrage Financier et Alignement Métier (MVP & Horizon 3 ans)
**Auteurs :** Équipe IA NutriScope

---

## 1. Synthèse du Modèle Comportemental en Magasin
Le projet NutriScope cible en priorité **Sophie Martin**, le persona cœur de cible représentant les parents pressés gérant les courses du foyer. Ses arbitrages en rayon obéissent aux métriques moyennes du marché :

* **Fréquence d'achat :** **2 à 3 sessions d'achat par semaine** pour le foyer (1 grand plein hebdomadaire de 1h40 + 1 à 2 sessions d'appoint).
* **Intensité d'usage mobile :** **4 consultations/scans de l'application par session d'achat**, pour une durée d'utilisation moyenne de **4,2 minutes** par session en rayon.
* **Volume d'usage annuel :** Sur la base de 2 sessions hebdomadaires qualifiées, un utilisateur type réalise **104 sessions par an**, générant un total de **416 comparaisons/scans de produits par an** (Hypothèse de cadrage utilisateur : 2 sessions x 4 comparaisons).

---

## 2. Pénétration du Marché & Potentiel d'Acquisition à 3 ans
Sur un marché français estimé à **40 millions de consommateurs équipés de smartphones** (Données macroéconomiques sectorielles), la pénétration des outils numériques d'aide à l'achat se segmente ainsi :

* **Utilisateurs Actifs (Déjà convertis) :** **45 % à 48 %** (utilisateurs réguliers d'applications comme Yuka ou Open Food Facts).
* **Le Vivier (Indécis à convertir) :** **35 %** des consommateurs, prêts à utiliser une application si elle lève la charge mentale en magasin.
* **Réfractaires :** **17 % à 20 %** (fracture numérique ou habitudes ancrées).

### Trajectoire d'Acquisition Mensuelle de NutriScope (Horizon 36 Mois)
L'objectif est d'atteindre **8,50 % de part de marché globale** à la fin de l'année 3, se traduisant par **3 400 000 Utilisateurs Actifs Mensuels (MAU)**. La croissance est modélisée selon un scénario de pénétration progressive (Post-déploiement de l'API au Mois 6) :

- **Mois 1 (Lancement Pilote) :** 0,04 % PDM | **15 700 MAU**
- **Mois 6 (Déploiement MVP / API) :** 0,58 % PDM | **231 000 MAU** *(Dépassement du KPI initial de 100k utilisateurs)*
- **Mois 12 (Fin Année 1) :** 1,64 % PDM | **654 000 MAU** *(Pénétration du vivier d'indécis)*
- **Mois 24 (Fin Année 2) :** 4,63 % PDM | **1 850 000 MAU** *(Accélération par intégration V2/V3 : profils & paniers complets)*
- **Mois 36 (Fin Année 3) :** 8,50 % PDM | **3 400 000 MAU** *(Maturité de la plateforme)*

---

## 3. Positionnement & Segments Différenciants de l'IA
Pour capter ces 3,4M d'utilisateurs face aux leaders du marché, NutriScope s'appuie sur quatre briques d'Intelligence Artificielle résolvant les frictions du parcours actuel (AS-IS) :

1. **IA d'Analyse et d'Évaluation Nutritionnelle :** Elle corrige automatiquement les risques de données manquantes ou incohérentes d'Open Food Facts (ex: sucres/sel > 100g) par des pipelines de nettoyage rejouables et des filtres de complétude (Prévu aux Mois 1 & 2 du planning).
2. **Moteur IA de Substitution :** Contrairement aux scanners bruts, il propose des alternatives directes dans la même catégorie de produit (Prévu au Mois 4).
3. **Assistant Conversationnel RAG :** Il vulgarise les données complexes (ex: traduire "17g de sucre" en conseil bienveillant et non culpabilisateur) pour réduire la fatigue informationnelle de Sophie Martin en rayon (Prévu au Mois 5).
4. **Filtre Multicritères (Évolutif) :** Permet à l'avenir de croiser le score nutritionnel avec des critères éthiques, allergènes (profil Marc Leboucher) ou RSE.

---

## 4. Modèle Économique & Projections du Chiffre d'Affaires (Scénario Pessimiste)
Conformément aux directives de la Direction et du DPO, le modèle évite tout conflit d'intérêts direct (pas de vente de données nominatives, pas de distorsion de concurrence entre industriels). Il repose sur un modèle **Freemium B2C** et de la **Data B2B anonymisée**.

### 📦 A. Abonnements Premium B2C (Scénario Plancher : Taux de conversion de 1,5 %)
La version gratuite offre le scan et le Nutri-Score. L'abonnement Premium (fixé à un tarif accessible de **2,99 € / mois**, soit **35,88 € / an**) débloque les fonctionnalités avancées : personnalisation des profils, alertes allergènes complexes et analyse automatique du panier complet (V3).

* **Nombre d'abonnés (Année 3) :** 3 400 000 MAU × 1,5 % = **51 000 abonnés Premium**
* **Chiffre d'Affaires Annuel Premium :** 51 000 × 35,88 € = **1 829 880 €**

### 📊 B. Monétisation de la Data B2B (Anonymisée et Agrégée)
Conformément au principe de minimisation du RGPD et sous l'encadrement du DPO, NutriScope valorise des indicateurs analytiques anonymisés (tendances de consommation, arbitrages de marques en direct en rayon) auprès des distributeurs et industriels pour optimiser leurs gammes.

* **Volume de scans brut généré / an :** 3,4M d'utilisateurs × 416 scans/an = **1,414 milliard de requêtes**.
* **Volume de Data exploitable et qualifiée :** Fixé à **20 %** du volume brut (scans complets avec arbitrage ou substitution validée) = **282,88 millions de lignes de données**.
* **Valorisation commerciale B2B :** Vendue sous forme de rapports de tendances au CPM (Coût Pour Mille) plancher de **5,00 €**.
* **Chiffre d'Affaires Annuel Data B2B :** (282 880 000 / 1 000) × 5,00 € = **1 414 400 €**

### 📈 C. Récapitulatif du Chiffre d'Affaires Global (Année 3)

| Source de Revenu | Métrique Clé | Chiffre d'Affaires Annuel (€) | Part du Mix (%) |
| :--- | :--- | :--- | :--- |
| **Abonnements Premium (B2C)** | 51 000 abonnés à 2,99€/mois | **1 829 880 €** | 56,4 % |
| **Analyses de Tendances (B2B)** | 282,8M de requêtes à 5€ CPM | **1 414 400 €** | 43,6 % |
| **TOTAL RÉCURRENT ESTIMÉ** | **Base de 3,4M d'utilisateurs** | **3 244 280 €** | **100 %** |

---

## 5. Matrice des Risques & Clauses de Conformité (Mise à jour Projet)
Le modèle financier et technique intègre les parades obligatoires liées aux contraintes de votre charte de cadrage :

* **Risque de Rupture de Confiance (Allergies/Diabète) :** Une erreur de l'assistant RAG ou du moteur de substitution sur un allergène est critique. 
  * *Parade :* Le positionnement reste strictement informatif et non médical. Un avertissement légal impose la vérification de l'étiquetage industriel physique en rayon avant achat.
* **Contrainte DPO & RGPD (Données Sensibles) :** Les préférences alimentaires et les allergies sont des données de santé au sens du RGPD.
  * *Parade :* Le paramétrage du profil utilisateur est facultatif. L'historique des requêtes utilisé pour la vente de données B2B est purgé de tout identifiant personnel (anonymisation irréversible et interdiction de revente nominative/concurrentielle).
* **Biais et Dépendance Open Food Facts :** Les erreurs de la base collaborative impactent directement les recommandations.
  * *Parade :* Mise en cache locale, création d'un référentiel interne NutriScope et contrôles qualité automatisés dès l'import du dataset maître (Mois 1 & 2 du planning).

---

## Footnote
This is for informational purposes only. For medical advice or diagnosis, consult a professional. AI responses may include mistakes.