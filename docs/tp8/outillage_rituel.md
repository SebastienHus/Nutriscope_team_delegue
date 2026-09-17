# Outillage de suivi et rituels d'équipe — Projet IA NutriScope
### TP 8 · Jalon J2 · Version v0.2

**Équipe :** Sébastien HUS / Nicolas CUSUMANO
**Date :** 17/09/2026

---

## 1. Outil de suivi retenu

### 1.1 Décision

L'équipe retient les tickets (« issues ») du dépôt de code (GitHub ou GitLab, déjà utilisé pour le versionnement et l'étiquetage des livraisons) plutôt qu'un tableau kanban séparé. La raison de ce choix est simple : le dépôt de code est l'outil que l'équipe ouvre déjà tous les jours pour committer, et c'est celui qui a le plus de chances d'être réellement tenu à jour dans la durée. Ajouter un second outil (un tableau externe de type Trello) aurait dispersé le suivi entre deux emplacements et aurait fait porter le risque, déjà identifié dans l'analyse des risques, d'un abandon de la documentation par manque de temps.

Le dépôt de code offre nativement une vue en tableau (colonnes À faire / En cours / En revue / Terminé) construite directement à partir des tickets et de leurs étiquettes, ce qui donne à l'équipe l'équivalent d'un tableau kanban sans changer d'outil.

### 1.2 Étiquettes retenues

Chaque ticket porte trois familles d'étiquettes, pour permettre de filtrer le backlog selon n'importe quel axe de lecture :

| Famille | Étiquettes | Usage |
|---|---|---|
| Priorité MoSCoW | `must-have`, `should-have`, `could-have`, `wont-have` | Reprend directement la priorisation du backlog produit. |
| Nature du travail | `donnee`, `modele-ia`, `interface`, `conformite`, `documentation` | Identifie la brique concernée (pipeline, modèle Nutri-Score, moteur de substitution, assistant, RGPD/AI Act). |
| Jalon | `jalon-J3`, `jalon-J4`, `jalon-J5`, `jalon-J6`, `jalon-J7` | Rattache chaque ticket au jalon du macro-planning auquel il contribue, pour vérifier en un coup d'œil l'avancement d'un jalon donné. |

### 1.3 Correspondance avec le backlog

Chaque histoire du backlog produit (US-01 à US-11) devient un ticket dans le dépôt dès l'ouverture du jalon qui la concerne, avec son estimation en points reportée dans le titre du ticket. Un ticket n'est fermé que lorsque ses critères d'acceptation, déjà rédigés dans le backlog, sont vérifiés — pas seulement lorsque le code est écrit.

---

## 2. Rituels d'équipe

Les rituels décidés simplifient et remplacent la cadence Scrum initialement esquissée dans le cahier des charges (sprint planning bimensuel, réunion d'avancement plusieurs fois par semaine) par une cadence alignée sur le rythme réel du projet fil rouge, qui avance par séance de travaux pratiques plutôt que par semaine calendaire.

### 2.1 Point d'équipe de 10 minutes en début de séance

À chaque début de séance de travail (TP), l'équipe tient un point de 10 minutes avec trois questions fixes : qu'est-ce qui a été fait depuis la dernière séance, qu'est-ce qui est prévu pour cette séance, et qu'est-ce qui bloque. Ce point remplace le stand-up hebdomadaire initialement prévu, mieux adapté à un rythme de projet réel qu'à un projet séquencé par séances de formation.

### 2.2 Revue à chaque jalon

À l'atteinte de chaque jalon (J3 à J7), l'équipe tient une revue qui reprend le même format que la revue de sprint : démonstration du livrable du jalon, vérification des critères d'acceptation des tickets fermés, et rétrospective courte (ce qui a bien fonctionné, ce qui doit changer avant le jalon suivant). Cette revue est celle qui alimente, le cas échéant, la présentation de validation devant la direction.

### 2.3 Ce que ces rituels ne remplacent pas

Le plan d'adoption prévoit, en aval de ces deux rituels internes, des points spécifiques avec des parties prenantes externes à l'équipe projet (comité d'adoption semestriel avec le sponsor, le marketing et le DPO ; boucle de retours hebdomadaire entre le support client et le responsable produit). Ces rituels-là restent distincts : ils portent sur l'adoption du produit une fois en usage, pas sur l'avancement du développement.

---

## 3. Auto-contrôle avant de committer

- [ ] Chaque ticket ouvert porte au moins une étiquette de priorité, une étiquette de nature et une étiquette de jalon.
- [ ] Le point de 10 minutes et la revue de jalon sont inscrits au calendrier de l'équipe, pas seulement décrits dans ce document.
- [ ] Le tableau du dépôt de code (vue kanban native) est accessible à l'ensemble de l'équipe et à la direction pour consultation.
- [ ] Aucun rituel ne mesure un KPI individuel : les revues portent sur l'avancement du jalon, jamais sur la performance d'une personne.