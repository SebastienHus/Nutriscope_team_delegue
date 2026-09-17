# Planning — Projet IA NutriScope
### Chemin de dépôt prévu : `docs/cadrage/planning.md`
### TP 8 · Jalon J2 · Version v0.2

**Équipe :** Sébastien HUS / Nicolas CUSUMANO
**Date :** 17/09/2026

---

## Principe du calendrier

Le projet est cadencé sur sept jalons datés, arbitrés avec la direction. Deux jalons sont déjà atteints à la date de ce document :

- **J1 — 1er septembre : base de données opérationnelle.** Base relationnelle modélisée et chargée, note d'exploration des données.
- **J2 — 17 septembre : note de cadrage, backlog et plan de pilotage** *(jalon visé par le présent TP)*. Note de cadrage, backlog produit outillé, présent document de planning, outil de suivi et rituels d'équipe.

Le présent document détaille les cinq jalons restants, J3 à J7, qui constituent le macro-planning à suivre à partir de maintenant.

---

## Jalon J3 — 14 octobre : socle data consolidé

| Travaux | Nature |
|---|---|
| Nettoyage et normalisation industrialisés du catalogue | Phase principale |
| Analyse exploratoire de référence (distributions, complétude, corrélations) | Phase principale |
| Bascule vers un format de stockage analytique adapté au volume | Phase principale |
| Pipeline de données rejouable en une seule commande | Phase principale |
| Tableaux de bord de suivi de la qualité des données | Consolidation |

**Livrable de jalon :** pipeline de données documenté, rapport d'analyse exploratoire, tableaux de bord — étiquette de version `v0.3`.
**Histoires du backlog concernées :** US-05 (pipeline automatisé d'ingestion et de nettoyage), US-15 (tableau de bord de la qualité du catalogue).
**Point d'attention :** les jeux d'entraînement et de test des modèles du jalon J4 sont figés à ce jalon, pas plus tard — un découpage documenté et gelé, faute de quoi les évaluations du jalon suivant ne seront pas comparables entre elles.

---

## Jalon J4 — 4 novembre : modèles d'intelligence artificielle évalués

| Travaux | Nature |
|---|---|
| Modèle prédictif du Nutri-Score (classification), comparé à des modèles de référence simples | Phase principale |
| Segmentation du catalogue par regroupement (identification de familles de produits comparables) | Phase principale |
| Moteur de substitution — première version fonctionnelle | Phase principale |
| Classifieur de catégorie de produit à partir d'une photo | Phase principale |
| Documentation des limites de chaque modèle (biais, cas d'échec) | Consolidation |

**Livrable de jalon :** modèles évalués (notebooks propres, métriques, limites documentées) — étiquette de version `v0.4`.
**Histoires du backlog concernées :** US-02 (transparence et Nutri-Score prédit), US-07 (détail explicatif de l'indice de confiance), US-14 (segmentation du catalogue), US-03 (recommandation d'alternatives), US-12 (classification de la catégorie d'un produit à partir d'une photo).
**Point d'attention :** chaque modèle est livré avec ses métriques, sa validation croisée et une note honnête sur ce qu'il rate. Le choix du modèle retenu pour l'application est tracé par écrit avec ses critères — performance, temps de réponse, simplicité de maintenance.

---

## Jalon J5 — 30 novembre : assistant conversationnel RAG validé

| Travaux | Nature |
|---|---|
| Constitution du corpus documentaire (catalogue et sources publiques de référence en nutrition) | Phase principale |
| Chaîne de récupération et génération de réponses (RAG), avec citation systématique des sources | Phase principale |
| Mesure de la qualité des réponses sur un jeu de questions de référence | Phase principale |
| Garde-fous testés par des mises à l'épreuve croisées entre équipes (questions pièges, tentatives de contournement) | Phase principale |
| Gel de la version de l'assistant avant intégration | Consolidation |

**Livrable de jalon :** assistant démontrable, rapport d'évaluation, version figée — étiquette de version `v0.5`.
**Histoire du backlog concernée :** US-04 (assistant nutritionnel conversationnel).
**Démarrage du plan d'adoption :** premières actions de communication (avis utilisateurs, campagne de sensibilisation interne et externe).

---

## Jalon J6 — 29 décembre : application stabilisée et déployée

| Travaux | Nature |
|---|---|
| Exposition des modèles via une interface applicative (API) | Phase principale |
| Application de démonstration branchée sur l'API | Phase principale |
| Conteneurisation et intégration continue (déploiement automatisé, sans intervention manuelle) | Phase principale |
| Mise en ligne accessible depuis un navigateur | Phase principale |
| Stabilisation en conditions d'autonomie d'équipe, revue de code croisée | Consolidation |

**Livrable de jalon :** application déployée et accessible, chaîne d'intégration continue opérationnelle — étiquette de version `v1.0`.
**Histoires du backlog concernées :** US-01 (scan et recherche de produit), US-06 (gestion des produits inconnus et des incertitudes).

### Entre J5 et J6 — la bêta utilisateurs

Une cohorte de vingt à trente bêta-testeurs est mobilisée sur l'application avant son ouverture. Cette fenêtre, qui n'est pas un jalon en soi, porte deux travaux distincts qu'il serait coûteux de repousser : les premiers retours d'usage réels, qui alimentent le plan d'adoption, et le test de l'offre payante — présentation de l'abonnement et mesure de l'intérêt réel, sans encaissement. C'est la seule occasion, avant l'ouverture au public, de confronter à des utilisateurs l'hypothèse la plus fragile du modèle économique.

---

## Jalon J7 — 14 janvier : produit final et conformité

| Travaux | Nature |
|---|---|
| Supervision, journaux structurés et tableau de bord d'exploitation | Phase principale |
| Rejeu automatisé des évaluations (assistant, Nutri-Score) pour détecter une dérive | Phase principale |
| Analyse de biais consolidée, rayon par rayon et classe par classe | Phase principale |
| Dossier de conformité (registre RGPD, positionnement AI Act, accessibilité RGAA, licences des données) | Phase principale |
| Documentation complète (installation, architecture, exploitation) | Phase principale |
| Répétition puis soutenance devant la direction | Phase principale |
| Consolidation du dossier de projet complet | Consolidation |

**Livrable de jalon :** produit final, documentation complète, soutenance.
**Histoires du backlog concernées :** US-16 (supervision de l'application en production) et US-13 (attribution des sources de données) — le crédit Open Food Facts et la vérification juridique de la valorisation B2B sont à boucler avant ce jalon.
**Plan d'adoption :** déploiement complet du dispositif d'accompagnement (formation du support client, mesure des indicateurs d'adoption, dispositif d'ancrage).

---

## Ce qui suit le jalon J7

Une période de mise en pratique hors projet (stage) est prévue avant la dernière ligne droite : reprise des retours de la soutenance, derniers correctifs strictement techniques, répétition générale, puis constitution des dossiers de certification par bloc de compétences. Ces travaux ne modifient pas le périmètre fonctionnel du produit livré au jalon J7 ; ils en consolident la preuve pour la certification.

---

## Vue d'ensemble

```
J1 ──── J2 ──── J3 ──── J4 ──── J5 ──── J6 ──── J7
01/09   17/09   14/10   04/11   30/11   29/12   14/01
Base    Cadrage Socle   Modèles Assis-  Appli   Produit
SQL     +       data    IA      tant    déployée final +
        backlog consolidé évalués RAG    stable  conformité
(atteints)      └──────────── restant à livrer ────────────┘
```

Ce planning sera revu à chaque jalon lors de la revue de fin de jalon (voir le document sur les rituels d'équipe et l'outillage) et ajusté si l'écart entre la charge réelle constatée et la charge estimée dans le backlog produit dépasse 20 %.
