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

Chaque histoire du backlog produit devient un ticket dans le dépôt dès l'ouverture du jalon qui la concerne, avec son estimation en points reportée dans le titre du ticket. Un ticket n'est fermé que lorsque ses critères d'acceptation, déjà rédigés dans le backlog, sont vérifiés — pas seulement lorsque le code est écrit.

### 1.4 Flux de travail dans le dépôt

Le dépôt fonctionne sur trois niveaux de branches : `main`, protégée, ne reçoit que du code relu et vert ; `dev` porte l'intégration courante ; une branche `feat/...` par sujet de travail. Aucune fusion vers `main` n'a lieu sans relecture par l'autre membre de l'équipe et sans que la chaîne d'intégration continue soit au vert. Les conventions d'équipe — format des messages de validation, taille attendue d'une demande de fusion, qui relit quoi — sont écrites dans un fichier `CONTRIBUTING.md` à la racine, et les données brutes restent hors du dépôt : seuls les scripts qui les produisent sont versionnés.

Chaque jalon est marqué par une étiquette de version (`v0.2` pour le présent jalon, puis `v0.3` à `v1.0`), ce qui permet de revenir à l'état exact du produit tel qu'il a été présenté à la direction.

### 1.5 Décisions d'architecture tracées

Les choix structurants qui engagent la suite du projet — modèle retenu pour la mise en production, mode d'accès au modèle de langage, technologie de l'interface de démonstration, recours ou non à un affinage de modèle — sont consignés dans de courtes notes de décision, une par choix, rangées dans `docs/decisions/`. Chacune tient en quelques paragraphes : le problème posé, les options envisagées, l'option retenue et le critère qui a tranché. L'intérêt n'est pas documentaire : c'est de pouvoir répondre, trois mois plus tard et devant la direction, à la question « pourquoi avez-vous fait ce choix-là ».

---

## 2. Rituels d'équipe

Les rituels décidés simplifient et remplacent la cadence Scrum initialement esquissée dans le cahier des charges (sprint planning bimensuel, réunion d'avancement plusieurs fois par semaine) par une cadence alignée sur le rythme réel du projet fil rouge, qui avance par séance de travaux pratiques plutôt que par semaine calendaire.

### 2.1 Point d'équipe de 10 minutes en début de séance

À chaque début de séance de travail (TP), l'équipe tient un point de 10 minutes avec trois questions fixes : qu'est-ce qui a été fait depuis la dernière séance, qu'est-ce qui est prévu pour cette séance, et qu'est-ce qui bloque. Ce point remplace le stand-up hebdomadaire initialement prévu, mieux adapté à un rythme de projet réel qu'à un projet séquencé par séances de formation.

### 2.2 Journal de bord, trois lignes par séance

À la fin de chaque séance, trois lignes sont ajoutées au journal de bord du projet : ce qui a été fait, ce qui a été décidé, ce qui reste bloqué. Trois lignes, pas un compte rendu — l'intérêt est que ce soit tenu toutes les séances plutôt que bien rédigé une fois sur trois. C'est ce journal qui permet de reconstituer l'historique des décisions au moment de rédiger le dossier final, et de faire remonter un blocage avant qu'il ne devienne un retard de jalon.

### 2.3 Revue à chaque jalon

À l'atteinte de chaque jalon (J3 à J7), l'équipe tient une revue : démonstration de ce qui fonctionne réellement — pas un exposé sur ce qui est prévu —, vérification des critères d'acceptation des tickets fermés, et rétrospective courte (ce qui a bien fonctionné, ce qui doit changer avant le jalon suivant). Cette revue est celle qui alimente la présentation de validation devant la direction.

### 2.4 Regards croisés avec une autre équipe

Le projet prévoit, à plusieurs reprises, de faire éprouver le travail de l'équipe par une équipe extérieure plutôt que par elle-même : relecture du code, déroulé du guide d'installation sur une machine qui n'a jamais vu le projet, évaluation en double aveugle des réponses de l'assistant, tentatives délibérées de le mettre en défaut, parcours de démonstration déroulé par quelqu'un qui n'a pas participé au développement. Ce n'est pas un rituel d'équipe au sens strict, mais c'est le mécanisme de contrôle qualité le plus efficace dont le projet dispose, et il vaut mieux le provoquer que l'attendre : l'équipe sollicite systématiquement ce regard extérieur à l'approche de chaque jalon plutôt qu'au moment où il est imposé.

### 2.5 Ce que ces rituels ne remplacent pas

Le plan d'adoption prévoit, en aval de ces deux rituels internes, des points spécifiques avec des parties prenantes externes à l'équipe projet (comité d'adoption semestriel avec le sponsor, le marketing et le DPO ; boucle de retours hebdomadaire entre le support client et le responsable produit). Ces rituels-là restent distincts : ils portent sur l'adoption du produit une fois en usage, pas sur l'avancement du développement.

---

## 3. Auto-contrôle avant de committer

- [ ] Chaque ticket ouvert porte au moins une étiquette de priorité, une étiquette de nature et une étiquette de jalon.
- [ ] Le point de 10 minutes et la revue de jalon sont inscrits au calendrier de l'équipe, pas seulement décrits dans ce document.
- [ ] Le journal de bord a bien trois lignes pour la dernière séance.
- [ ] La branche `main` est protégée et le fichier `CONTRIBUTING.md` existe à la racine du dépôt.
- [ ] Tout choix structurant pris depuis le dernier jalon a sa note de décision dans `docs/decisions/`.
- [ ] Le tableau du dépôt de code (vue kanban native) est accessible à l'ensemble de l'équipe et à la direction pour consultation.
- [ ] Aucun rituel ne mesure un KPI individuel : les revues portent sur l'avancement du jalon, jamais sur la performance d'une personne.
