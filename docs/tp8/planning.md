# Planning — Projet IA NutriScope
### Chemin de dépôt prévu : `docs/cadrage/planning.md`
### TP 8 · Jalon J2 · Version v0.2

**Équipe :** Sébastien HUS / Nicolas CUSUMANO
**Date :** 17/09/2026

---

## Principe du calendrier

Le projet est cadencé sur huit mois et sept jalons numérotés (J1 à J7), chaque jalon correspondant à la validation d'un bloc fonctionnel avant de passer au suivant. Deux jalons sont déjà atteints à la date de ce document :

- **J1 — Base de données opérationnelle (Mois 1)** : profilage complet du jeu de données, définition du périmètre data, modélisation relationnelle, construction du jeu de données maître.
- **J2 — Pipeline de nettoyage validé (Mois 2)** *(jalon visé par le présent TP)* : normalisation des données, pipeline de nettoyage rejouable, indicateurs de complétude, segmentation des sous-ensembles de données.

Le présent document détaille les cinq jalons restants, J3 à J7, qui constituent le macro-planning à suivre à partir de maintenant.

---

## Mois 3 — Modèle Nutri-Score → Jalon J3

| Travaux | Nature |
|---|---|
| Sélection du jeu de données complet | Phase principale |
| Entraînement du modèle prédictif de Nutri-Score | Phase principale |
| Validation croisée | Phase principale |
| Analyse des biais du modèle | Phase principale |
| Documentation du modèle | Consolidation |

**Livrable de jalon :** modèle Nutri-Score validé.
**Histoires du backlog concernées :** US-02 (transparence et Nutri-Score prédit), US-07 (détail explicatif de l'indice de confiance).

---

## Mois 4 — Moteur de substitution → Jalon J4

| Travaux | Nature |
|---|---|
| Définition des règles de substitution | Phase principale |
| Construction du moteur de recommandation | Phase principale |
| Tests sur plusieurs rayons | Phase principale |
| Ajustements et documentation | Consolidation |

**Livrable de jalon :** moteur de substitution opérationnel — **lancement de la version publique (v1.0)**.
**Histoires du backlog concernées :** US-03 (recommandation d'alternatives).
**Point de vigilance porté à ce jalon :** c'est avant ce jalon que le taux de conversion vers l'abonnement Premium doit avoir été testé auprès d'un échantillon réel d'utilisateurs (200 à 300 personnes), condition de fiabilité du modèle de retour sur investissement présenté dans la note de cadrage.

---

## Mois 5 — Assistant conversationnel RAG → Jalon J5

| Travaux | Nature |
|---|---|
| Construction du corpus documentaire (catalogue et sources publiques) | Phase principale |
| Vectorisation et indexation du corpus | Phase principale |
| Développement de l'assistant conversationnel | Phase principale |
| Tests de robustesse (absence d'information inventée) | Phase principale |
| Documentation de l'assistant | Consolidation |

**Livrable de jalon :** assistant conversationnel validé.
**Histoires du backlog concernées :** US-04 (assistant nutritionnel conversationnel).
**Démarrage du plan d'adoption :** premières actions de communication (avis utilisateurs, campagne de sensibilisation interne et externe).

---

## Mois 6 — Interface applicative et déploiement → Jalon J6

| Travaux | Nature |
|---|---|
| Exposition des modèles via une interface applicative | Phase principale |
| Conteneurisation de l'application | Phase principale |
| Déploiement en environnement de production | Phase principale |
| Mini-application de démonstration | Phase principale |
| Documentation technique | Consolidation |

**Livrable de jalon :** interface applicative et déploiement opérationnels. C'est à ce jalon que le projet atteint le niveau d'audience prévu de 231 000 utilisateurs actifs mensuels — soit déjà plus du double du seuil de 100 000 utilisateurs fixé initialement par la direction.

---

## Mois 7 — Conformité et qualité → Jalon J7

| Travaux | Nature |
|---|---|
| Registre des traitements RGPD | Phase principale |
| Consolidation de l'analyse de biais | Phase principale |
| Positionnement au regard du règlement européen sur l'intelligence artificielle (AI Act) | Phase principale |
| Contrôle de l'accessibilité numérique (référentiel RGAA) | Phase principale |
| Documentation de conformité | Consolidation |

**Livrable de jalon :** conformité validée.
**Plan d'adoption :** déploiement complet du dispositif d'accompagnement (formation du support client, mesure des indicateurs d'adoption, dispositif d'ancrage).

---

## Mois 8 — Dossier final et soutenance

| Travaux | Nature |
|---|---|
| Rédaction du dossier final | Phase principale |
| Préparation de la soutenance | Phase principale |
| Tests finaux de l'application | Phase principale |
| Corrections et stabilisation | Consolidation |

**Livrable final :** application NutriScope et dossier complet du projet.

---

## Vue d'ensemble

```
J1 ──── J2 ──── J3 ──── J4 ──── J5 ──── J6 ──── J7 ──── Soutenance
M1      M2      M3      M4      M5      M6      M7      M8
Base    Pipeline Modèle  Substi- Assis-  API +   Confor- Dossier
SQL     validé   Nutri-  tution  tant    déploi- mité    final
                 Score           RAG     ement
(atteints)       └──────────── restant à livrer ────────────┘
```

Ce planning sera revu à chaque jalon lors de la revue de fin de jalon (voir le document sur les rituels d'équipe et l'outillage) et ajusté si l'écart entre la charge réelle constatée et la charge estimée dans le backlog produit dépasse 20 %.