# PROJET FIL ROUGE NUTRISCOPE · TP 7 (SUITE) — CONDUITE DU CHANGEMENT & ACCOMPAGNEMENT
## Trame à remplir — plan d'adoption NutriScope

**Équipe / membres :** Sébastien HUS / Nicolas CUSUMANO  
**Date :** 15/09/2026  

---

> **Consigne :** remplissez chaque section de ce document, puis committez-le dans votre dépôt d'équipe sous `docs/cadrage/plan_adoption.md` et complétez l'onglet « adoption » de `kpi_roi.xlsx`. Ce document alimente la note de cadrage du TP 8 (jalon J2).  
> **Règle du jeu :** interdiction d'écrire « communiquer davantage » ou « former les utilisateurs » sans dire qui, quand, sur quoi, et comment on saura que ça a marché.

---

## 1. Cartographie des acteurs de l'adoption

* **Pouvoir :** faible / moyen / fort  
* **Catégorie :** à mobiliser / à sécuriser / à informer / à suivre  
* *Une action concrète et datée par acteur — pas la même pour tous. Les acteurs sont pré-listés ; ajoutez les vôtres dans les lignes vides.*

| Acteur | Pouvoir | Attitude | Catégorie | Action concrète (30j) |
| :--- | :--- | :--- | :--- | :--- |
| **Direction NutriScope (sponsor)** | Fort | Allié | À mobiliser | Transparence, échanges, les faire parler, rapport d'avancement à chaque fin de sprint |
| **Marketing** | Moyen | Allié | À mobiliser | Leur donner de la visibilité, Protéger leur engagement, Co-conception de campagne de lancement |
| **Support client** | Faible | Neutre | À activer | Ambassadeurs, Formation de 2h de RGPD/AI Act |
| **Équipe data/IA** | Faible | Neutre | À activer | Propositions, Tests de nouveautés, Revue en fin de sprint des cas d'erreurs ou d'hallucinations |
| **DPO** | Fort | Opposant | À sécuriser | Ecoute individuelle, Traitement des objections, Validation AIPD et protocole d'anonymisation des données |
| **Utilisateurs — parent pressé** | Faible | Neutre | À activer | Témoignages, Tests d'usabilité de 15min |
| **Utilisateurs — personne diabétique** | Faible | Allié | À activer | Ambassadeur, Retours Utilisateur, Focus group UX |
| **Utilisateurs — étudiant sportif** | Faible | Neutre | À activer | Tests de nouveauté, Bêta-test ouvert de deux semaines |
| **Open Food Facts** | Faible | Neutre | À informer | Note d'information technique concernant l'utilisation de leur API |
| **Professionnels de santé** | Faible | Neutre | À activer | Témoignages, Retours métiers |
| **Financeurs** | Fort | Neutre | À sécuriser | Communication régulière, Ecoute individuelle, Transmission de rapport de cadrage et KPI/ROI |

---

## 2. Anticipation des résistances

> **Nature :** rationnelle / émotionnelle / politique.  
> Une résistance rationnelle est une information sur un défaut réel du produit : notez ce qu'elle vous apprend et la réponse produit (pas seulement un discours).

### Résistances internes

| Résistance | Nature | Réponse proposée |
| :--- | :--- | :--- |
| **DPO** : Refus du traitement des données de santé sans garanties juridiques strictes. | Rationnelle + politique | **Produit** : Stockage local (sur l'appareil) des données de santé (ex. diabète) et aucune centralisation nominative sur les serveurs. |
| **Equipe Data/AI** : Inquiétude sur la fiabilité des données sources Open Food Facts (données incomplètes ou erronées). | Rationnelle | **Produit** : Déploiement d'un filtre automatique de validation des données (exclusion des fiches incomplètes et alerte sur valeurs aberrantes). |
| **Support Client** : Crainte d'être incapable d'expliquer une recommandation IA contestée par un utilisateur. | Emotionnelle | **Accompagnement** : Rédaction d'un kit de réponses (FAQ 15 Q/R) et accès à un outil d'explicabilité des règles nutritionnelles |

### Freins utilisateurs

| Frein | Nature | Réponse proposée |
| :--- | :--- | :--- |
| **Manque de temps** : Peur que l'application soit trop longue à utiliser en faisant ses courses. | Émotionnelle / Rationnelle | **Produit** : Scanner instantané de code-barres restituant le verdict nutritionnel en moins de 2 secondes. |
| **Difficulté à comparer** : Hésitation entre plusieurs produits similaires en rayon. | Rationnelle | **Produit** : Écran de comparaison côte à côte avec mise en exergue visuelle (code couleur + forme pour accessibilité) des éléments sains et problématiques. |
| **Terminologie difficile** : Incompréhension du jargon nutritionnel ou des étiquettes brutes. | Émotionnelle | **Produit** : Traduction automatique des apports en équivalents visuels simples (ex. : nombre de morceaux de sucre, présence d'additifs ultra-transformés). |

---

## 3. Plan d'adoption en trois volets

> Le message central dit ce que NutriScope fait ET ce qu'il ne fait pas. Chaque action est reliée à un stade ADKAR (*Awareness, Desire, Knowledge, Ability, Reinforcement*) et positionnée sur le calendrier réel du projet (jalons J5 à J7).

**Message central du produit :**  

| Volet | Stade ADKAR | Actions NutriScope | Cible | Quand |
| :--- | :--- | :--- | :--- | :--- |
| **Communiquer** | **D**esire | Avis Utilisateurs | Utilisateurs | J5 |
|  | **K**nowledge | Mise à jour de fonctionnalités | Utilisateurs | J7+ |
|  | **K**nowledge | Limites d'Usage Réglementaire et Technique | Tous | J6 |
|  | **A**wareness | Campagne de teasing interne/externe sur les apports nutritifs des produits alimentaires | Tous | J5 |
| **Accompagner** | **K**nowledge + **A**bility  | Documentations à fournir à l'équipe, Atelier pratique de 2h sur la résolution des requêtes IA/RGPD (Validé par la réussite à un QCM de fin de session) | Support Client | J7+ |
| **Mesurer** | **A**bility + **R**einforcement | Sondage Utilisation | Equipe Data et Comité | J5 |
|  | **K**nowledge | Nombre d'occurences d'un même sujet (Tickets) | Support Client | J7+ |

> **Message Central** : NutriScope simplifie la lecture des étiquettes et guide vos choix alimentaires du quotidien en toute transparence. NutriScope ne pose aucun diagnostic médical et ne remplace pas un suivi professionnel de santé.
---

## 4. KPI d'adoption (onglet « adoption » du `kpi_roi.xlsx`)

> 4 à 5 KPI avec leur définition exacte (qui compte, sur quelle période), un seuil d'alerte et le plan de relance. Attention au piège du taux d'activation ; les mesures restent collectives, jamais individuelles.

| KPI | Définition exacte | Seuil d'alerte | Plan de relance |
| :--- | :--- | :--- | :--- |
| Scans par jour actif | Nombre moyen de scans réalisés par utilisateur actif et par jour | `< 0,8 scan/j actif` | • **Technique** : Optimiser la latence T1, mettre en cache les métadonnées, enrichir la BDD sur les rayons faibles.<br>• **UI/UX** : Améliorer le composant de capture (guidage visuel, feedback haptique/sonore), rendre le bouton de scan plus accessible. |
| Taux d'activation à J7 | Part des nouveaux inscrits ayant scanné au moins un produit dans les 7 jours suivant l'inscription | `< 40 %` | • **UI/UX :** Simplifier le parcours d'accueil (*Time to First Scan*), ajouter un *pre-prompt* d'explication pour l'accès caméra.<br>• **Growth :** Configurer une relance auto (push/e-mail) à **J+2-J+3** pour les inscrits n'ayant pas encore scanné. |
| Rétention à 30 jours | Part des utilisateurs actifs au mois M qui reviennent au mois M+1 | `< 20 %` | • **User Research :** Déclencher un questionnaire/feedback *in-app* auprès des inactifs depuis 15 jours.<br>• **Growth :** Envoyer des rappels contextualisés (nouveaux rayons, substitutions) et valoriser la valeur accumulée (historique/panier). |
| Taux de substitution acceptée | Part des recommandations de substitution effectivement retenues par l'utilisateur (clic + confirmation) | `< 8 %` | • **Data / ML :** Ré-entraîner et affiner le modèle de recommandation ; compléter le catalogue sur les rayons sous-performants.<br>• **UI/UX :** Mieux afficher les arguments de substitution (Nutri-Score, prix) et intégrer un micro-feedback lors des refus. |
| Taux de réponses assistant sourcées | Part des réponses de l'assistant conversationnel appuyées sur une donnée produit identifiée (pas d'information inventée) | `< 80 %` | • **Data / LLM :** Enrichir la BDD documentaire, ré-entraîner / ajuster les prompts RAG pour forcer le *grounding* (citations).<br>• **Growth / CRM :** Après ré-entraînement, offrir **X mois gratuits sur le compte payant** aux bêta-testeurs / utilisateurs impactés. |
| Coût par requête assistant | Coût moyen (consommation du modèle de langage) d'une conversation avec l'assistant conversationnel | `> 0,03 €` | • **Prompt Eng. :** Réduire le contexte transmis au strict nécessaire.<br>• **Infra :** Mettre en place un cache sémantique et une FAQ/réponses courantes pré-calculées.<br>• **Routing :** Définir une stratégie multi-modèles (réserver le modèle coûteux aux abonnés payants / cas complexes, basculer le gratuit sur un modèle plus léger). |

---

## 5. Dispositif d'ancrage

> Décrivez un dispositif qui survit à la fin du projet : qui, à quelle fréquence, avec quel livrable.

| Élément | Point de Production | Qui | Fréquence | Livrable |
| :--- | :--- | :--- | :--- | :--- |
| **Ambassadeurs** | Relais terrain | 5 utilisateurs référents + 1 membre du Support Client | Trimestrielle | Rapport de retours terrain et propositions d'amélioration d'usage. |
| **Boucle de retours** | Feedback Loops | Support Client & Product Owner | Hebdomadaire | Synthèse catégorisée des tickets de support et des avis In-App, Backlog |
| **Comité d'adoption** | Inspect & Adapt | Sponsor, Responsable Marketing et DPO | Semestrielle | Bilan global des indicateurs d'usage et décisions de cadrage stratégique |
| **Évolutions du modèle** | DataOps & MLOps | Équipe Data/IA | Tous les 6 mois | Rapport d'audit de performance des algorithmes et réalignement scientifique |

---

> **Auto-contrôle avant de committer :** chaque action a un qui / quand / comment on le saura ; aucun KPI individuel ; le taux d'activation n'est pas vendu comme un succès ; au moins une résistance a été traitée comme une information produit.
