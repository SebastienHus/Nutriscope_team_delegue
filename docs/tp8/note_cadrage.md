# Note de cadrage — Projet IA NutriScope
### Version v0.2

**Équipe :** Sébastien HUS / Nicolas CUSUMANO
**Date :** 17/09/2026
**Sources :** note de cadrage initiale initiale, cahier des charges, analyse des risques, benchmark, note KPI/coûts/ROI, plan d'adoption
**Statut :** consolidée pour validation (direction / formateur)

---

## Préambule

Après huit exercices preparatoire de cadrage cette note réunit dans un seul document ce qui doit désormais servir de référence unique au pilotage du projet : 
 - le besoin
 - le périmètre
 - les parties prenantes
 - les indicateurs de performance et de retour sur investissement
 - les risques avec leurs plans de mitigation
 - le calendrier des prochains jalons (J3 à J7). 
  
  Elle ne reformule pas les analyses détaillées déjà produites — elle les synthétise et les arbitre là où plusieurs versions coexistaient, pour qu'une seule ligne directrice reste opposable à l'équipe et à la direction.

---

## 1. Contexte et besoin

### 1.1 Le problème à résoudre

En magasin, un consommateur qui veut comparer deux produits alimentaires perd aujourd'hui plus d'une minute par produit : l'étiquette nutritionnelle est dense, le Nutri-Score n'est renseigné que sur 44,9 % des références commercialisées en France (constat établi lors de l'exploration du jeu de données Open Food Facts), et aucun outil simple ne propose une alternative plus saine au moment même du choix. Cette charge mentale touche en priorité les parents qui gèrent les courses du foyer sous contrainte de temps — le persona central du projet, **Sophie Martin**, 38 ans qui réalise ses courses deux à trois fois par semaine et doit arbitrer en rayon sans disposer d'une information fiable et immédiate.

### 1.2 Le besoin validé par la direction

Un entretien semi-directif conduit avec la direction a confirmé que l'application attendue doit être intelligente, simple, personnalisée, fiable et accessible au plus grand nombre, sans jamais se substituer à un avis médical. La direction a validé Sophie Martin comme cible prioritaire du MVP (version minimale commercialisable) et a positionné quatre fonctionnalités comme indispensables dès la première version : la recherche et l'identification d'un produit (scan de code-barres ou recherche manuelle), une fiche produit synthétique compréhensible sans connaissance nutritionnelle, la comparaison de plusieurs produits, et un assistant conversationnel de recommandation. Les profils spécialisés — personnes diabétiques ou allergiques, sportifs, professionnels de santé — sont reconnus comme porteurs de valeur mais ne constituent pas la cible du MVP ; ils sont traités comme des évolutions.

### 1.3 La réponse produit

NutriScope répond à ce besoin par quatre briques d'intelligence artificielle complémentaires : 
 - un pipeline de nettoyage qui fiabilise la base Open Food Facts
 - un modèle prédictif de Nutri-Score qui comble les fiches incomplètes
 - un moteur de substitution qui propose des alternatives plus saines dans le même rayon
 - un assistant conversationnel qui vulgarise l'information sans jamais inventer de réponse (fonctionnement dit RAG — retrieval-augmented generation : le système va chercher des documents pertinents avant de générer sa réponse, pour l'ancrer sur des sources vérifiées, plutôt que de laisser le modèle de langage répondre de mémoire). 
  
  Le positionnement reste strictement informatif : NutriScope aide à choisir, il ne diagnostique pas et ne remplace pas un professionnel de santé — un principe rappelé par la direction elle-même comme la ligne rouge du projet.

---

## 2. Parties prenantes

### 2.1 Cartographie pouvoir / intérêt

| Partie prenante | Pouvoir | Intérêt | Posture retenue |
|---|---|---|---|
| Direction / commanditaires | Fort | Fort | Acteur à mobiliser en premier : valide chaque jalon et arbitre les choix économiques (taux de conversion, partenariats). |
| DPO (délégué à la protection des données) | Fort | Fort | Acteur à sécuriser : dispose d'un droit de blocage sur toute fonctionnalité touchant à des données de santé (allergies, diabète). |
| Financeurs | Fort | Faible | À informer régulièrement par un reporting court (avancement, KPI, ROI), sans les solliciter sur le détail opérationnel. |
| Marketing | Moyen | Fort | À mobiliser : porte le lancement, l'acquisition et le référencement sur les stores dès les premiers mois, période où la priorité est d'exister et de recruter. |
| Équipe projet | Moyen | Fort | Pilote l'exécution au quotidien. |
| Équipe data / IA | Faible | Fort | Peu d'impact décisionnel en phase de lancement (base d'utilisateurs encore trop réduite pour des analyses de comportement significatives), mais contribution technique déterminante. |
| Utilisateurs finaux (Sophie Martin et les autres personas) | Faible | Fort | Cible du produit ; à activer par des tests d'usabilité et des retours réguliers plutôt que par une consultation formelle. |
| Professionnels de santé | Faible | Moyen | À associer pour la crédibilité de l'application et pour un avis métier sur les recommandations. |
| Open Food Facts | Faible | Faible | Fournisseur de données à informer des usages faits de sa base. |

Deux arbitrages structurent cette cartographie : le Marketing pèse davantage que son pouvoir formel ne le suggère, car la priorité des premiers mois est l'existence sur les stores ; à l'inverse, l'équipe data ne pourra peser sur les décisions produit qu'une fois une base d'utilisateurs suffisante constituée pour objectiver ses recommandations.

### 2.2 Suite donnée en aval : le plan d'adoption

Cette cartographie a été affinée dans un plan d'adoption dédié, qui détaille pour onze acteurs (dont le support client, les trois profils d'utilisateurs et les financeurs) une action datée et nommée — jamais une intention générique de type « mieux communiquer ». Ce plan, aligné sur les jalons J5 à J7 du présent calendrier (§5), n'est pas repris intégralement ici : il reste la référence opérationnelle pour la conduite du changement et sera activé à l'approche du lancement public.

---

## 3. Périmètre

### 3.1 Ce qui est inclus dans le MVP

Le périmètre du MVP est restreint à cinq à huit rayons alimentaires principaux de la grande distribution, pour garantir la précision du moteur de substitution avant toute extension. Il comprend :

- le pipeline automatisé d'ingestion et de nettoyage du catalogue Open Food Facts ;
- le scan de code-barres et la recherche textuelle instantanée d'un produit ;
- la fiche produit synthétique, avec Nutri-Score réel ou prédit et un indice de confiance affiché systématiquement ;
- le moteur de substitution, qui propose une à trois alternatives plus saines dans la même catégorie ;
- l'assistant conversationnel RAG, limité aux données factuelles vérifiées ;
- la gestion explicite des cas d'incertitude (produit inconnu, données insuffisantes).

### 3.2 Ce qui est différé (évolutions V2 et V3)

L'historique des scans, la gestion des favoris et le profil utilisateur avec filtres d'allergènes sont classés en évolution V2 : ils demandent une base d'utilisateurs déjà active pour avoir du sens. La personnalisation avancée des recommandations selon un objectif nutritionnel du foyer est envisagée en V3.

### 3.3 Ce qui est explicitement hors périmètre

La reconnaissance visuelle d'étiquette par photographie (traitement dit de vision par ordinateur) et l'application mobile native complète sont exclues du MVP : le déploiement initial se fait sous forme d'une interface web de démonstration adossée à une API. Cette exclusion n'est pas un renoncement mais un séquencement : la robustesse du cœur data et des trois briques IA prioritaires (Nutri-Score, substitution, assistant) doit être acquise avant d'ouvrir de nouveaux canaux de saisie.

---

## 4. Indicateurs de performance et retour sur investissement

### 4.1 Les indicateurs de cadrage validés par la direction

Lors de l'entretien de cadrage, la direction a fixé quatre critères de succès pour le projet : 100 000 utilisateurs à terme, 33 % d'utilisateurs actifs mensuels, 40 % de fidélisation (réutilisation de l'application), et une note moyenne supérieure à 4,3 sur 5 sur les stores applicatifs. La trajectoire d'acquisition retenue pour le projet dépasse déjà largement le premier seuil dès le sixième mois (231 000 utilisateurs actifs mensuels projetés), ce qui déplace l'enjeu réel du projet de la seule acquisition vers la fidélisation et la rentabilité — les deux points que les indicateurs produit ci-dessous viennent surveiller de près.

### 4.2 Les six indicateurs produit et leurs seuils d'alerte

Six indicateurs de performance (KPI — indicateur clé de performance : une mesure choisie parce qu'elle est mesurable, rattachable à une équipe précise, et qu'elle déclenche une action lorsqu'un seuil est franchi) encadrent le pilotage opérationnel. Chacun est relié à un objectif métier et associé à un seuil d'alerte déclenchant un plan d'action déjà défini :

| Indicateur produit | Cible | Seuil d'alerte |
|---|---|---|
| Scans par jour actif | ≥ 1,5 scan/jour à M6 | < 0,8 |
| Taux d'activation à 7 jours | ≥ 60 % à M6 | < 40 % |
| Rétention à 30 jours | ≥ 40 % à M12 | < 20 % |
| Taux de substitution acceptée | ≥ 15 % à M12 | < 8 % |
| Taux de réponses de l'assistant sourcées | ≥ 90 % dès la mise en production | < 80 % |
| Coût par requête de l'assistant | ≤ 0,02 € par conversation | > 0,03 € |

Ces six indicateurs, leur baseline, leur responsable de suivi et leur lien avec les objectifs métier (fidéliser, monétiser, tenir les coûts, rassurer) sont détaillés dans l'arbre des indicateurs NutriScope, publié séparément et tenu à jour à chaque révision.

### 4.3 Le coût du projet et son retour sur investissement

Le coût total de possession (TCO) du projet, structuré en quatre familles — construction initiale, fonctionnement courant, accompagnement au changement, conformité réglementaire — s'établit à 237 618 € cumulés à douze mois, 518 919 € à vingt-quatre mois et 1 028 670 € à trente-six mois. Ce montant est identique dans les trois scénarios de revenus retenus : seul ce que le projet encaisse varie d'un scénario à l'autre, pas ce qu'il dépense.

Le modèle de revenus repose sur un abonnement Premium à 2,99 € par mois et sur des contrats de valorisation de données anonymisées auprès de distributeurs. Le taux de conversion vers l'abonnement Premium — arbitré avec la direction par prudence, en l'absence de tout test de vente réel — est le paramètre qui pèse le plus sur la rentabilité :

| Scénario | Taux de conversion Premium | ROI à 12 mois | ROI à 24 mois | ROI à 36 mois | Mois de rentabilité |
|---|---|---|---|---|---|
| Pessimiste | 0,7 % | −67,9 % | −23,3 % | +4,0 % | Mois 34 |
| Normal (central) | 1 % | −44,1 % | +18,8 % | +55,6 % | Mois 20 |
| Optimiste | 2 % | +16,9 % | +142,3 % | +214,8 % | Mois 11 |

**Lecture retenue pour le pilotage :** aucun scénario n'est rentable dès la première année. Le scénario central ne devient rentable qu'au bout d'environ vingt mois, porté surtout par la croissance du nombre d'utilisateurs actifs plutôt que par le taux de conversion lui-même. Vérifier ce taux de conversion avant le jalon J4 (lancement de la version publique) est donc la priorité absolue de validation économique du projet, avant même la maîtrise des coûts.

---

## 5. Risques et plans de mitigation

L'analyse des risques distingue un risque critique et cinq risques importants, tous liés à la qualité, à la complétude ou à la disponibilité des données, à l'exception du risque réglementaire :

| Risque | Probabilité | Impact | Niveau | Plan de mitigation retenu |
|---|---|---|---|---|
| **R1 — Données nutritionnelles incohérentes** (valeurs de sucre ou de sel supérieures à 100 g, énergie négative) | Élevée | Élevé | 🔴 Critique | Exclusion des produits présentant des incohérences majeures des jeux d'entraînement et des calculs affichés à l'utilisateur ; conservation des données brutes à des fins d'audit uniquement. |
| **R2 — Produits incomplets** (ingrédients, Nutri-Score ou valeurs nutritionnelles manquants) | Élevée | Moyen | 🟠 Important | Analyse partielle autorisée lorsque les données critiques sont présentes, avec affichage systématique d'un indice de confiance plutôt qu'un rejet pur et simple. |
| **R3 — Hétérogénéité des formats de données** (pays, catégories, unités multiples) | Élevée | Moyen | 🟠 Important | Normalisation automatisée à l'import et constitution de référentiels internes, plutôt qu'une correction manuelle au cas par cas. |
| **R4 — Dépendance à la source unique Open Food Facts** | Moyenne | Élevé | 🟠 Important | Mise en cache locale des produits les plus consultés, synchronisation périodique, et architecture ouverte à l'intégration future d'autres sources (par exemple la table CIQUAL). |
| **R5 — Évolution de la réglementation sur les données sensibles** (allergies, préférences alimentaires) | Faible | Élevé | 🟠 Important | Minimisation des données collectées, consentement explicite, droit de modification et de suppression, politique de confidentialité transparente ; stockage local des données de santé sans centralisation nominative côté serveur. |
| **R6 — Recommandations peu pertinentes** (moteur de substitution ou assistant) | Moyenne | Élevé | 🟠 Important | Priorité aux règles métier explicables sur les modèles d'apprentissage tant que l'historique de données est insuffisant ; introduction progressive de modèles prédictifs après validation de leur qualité. |

La matrice probabilité × impact associée classe ces risques selon une échelle à trois niveaux : rouge pour un plan de mitigation obligatoire avant tout passage en production, orange pour un plan à définir avant le jalon concerné, jaune pour un risque à surveiller sans action immédiate — aucun risque du projet ne se situe aujourd'hui dans cette dernière catégorie.

Deux risques complémentaires, de nature non technique, restent surveillés en aval de ce tableau : le risque de conflit d'intérêt lié aux partenariats de marques (mise en avant d'un produit partenaire dans une recommandation présentée comme neutre) et le risque de perte de confiance en cas d'erreur de l'assistant sur un allergène ou un profil diabétique — ce dernier étant considéré par la direction comme le risque le plus grave que le projet puisse encourir, la réputation de l'application étant son actif le plus important.

Six principes directeurs se dégagent de cette analyse et s'appliquent à l'ensemble du projet : la qualité prime sur la quantité de données conservées, la transparence est systématique dès qu'une information est incertaine, la normalisation des données est automatisée plutôt que manuelle, les dépendances externes sont réduites par la mise en cache et l'ouverture à d'autres sources, l'introduction de l'intelligence artificielle reste progressive et maîtrisée, et l'ensemble des indicateurs et modèles est réévalué en continu.

---

## 6. Macro-planning : des jalons J3 à J7

Le projet est structuré en sept jalons sur huit mois. Les jalons J1 (base de données opérationnelle) et J2 (pipeline de nettoyage validé) sont atteints à la clôture de ce TP8. Le calendrier ci-dessous couvre les cinq jalons restants, qui conduisent le projet du modèle prédictif jusqu'à la conformité réglementaire.

| Jalon | Période | Objectif | Livrables |
|---|---|---|---|
| **J3** | Mois 3 | Modèle Nutri-Score validé | Modèle prédictif entraîné et validé par validation croisée, analyse des biais, documentation du modèle |
| **J4** | Mois 4 | Moteur de substitution opérationnel | Règles de substitution définies, moteur testé sur plusieurs rayons, ajustements documentés |
| **J5** | Mois 5 | Assistant conversationnel RAG validé | Corpus vectorisé, assistant testé pour sa robustesse (absence d'hallucination), documentation |
| **J6** | Mois 6 | API et déploiement opérationnels | API exposant les modèles, conteneurisation, déploiement, mini-application de démonstration |
| **J7** | Mois 7 | Conformité validée | Registre RGPD, positionnement AI Act, accessibilité, consolidation de l'analyse de biais |

Un huitième mois, hors jalon numéroté, est réservé à la rédaction du dossier final et à la préparation de la soutenance.

Ce calendrier porte deux décisions déjà arbitrées avec la direction et rappelées ici pour mémoire opérationnelle : le taux de conversion Premium doit être testé sur un échantillon d'utilisateurs avant le jalon J4 (lancement public), et le plan d'adoption — communication, accompagnement, mesure — s'active à partir du jalon J5 pour être pleinement déployé au jalon J7.

---

## 7. Synthèse

Le projet NutriScope dispose désormais d'un cadrage complet et cohérent : un besoin validé par la direction et centré sur un persona prioritaire clairement identifié, un périmètre MVP resserré sur cinq à huit rayons et quatre briques d'intelligence artificielle, des indicateurs de performance et un modèle de retour sur investissement chiffrés sur trois scénarios, une analyse des risques assortie de plans de mitigation retenus, et un calendrier détaillé jusqu'au jalon J7. Le backlog produit outillé et priorisé, l'outil de suivi retenu par l'équipe et les rituels d'équipe qui l'accompagnent font l'objet des documents associés à cette note.

Le point de vigilance à porter à la connaissance de la direction lors de la revue de ce jalon reste le même que celui déjà identifié dans le chiffrage financier : la rentabilité du scénario central repose sur un taux de conversion Premium qui n'a encore jamais été testé auprès d'un utilisateur réel. Sa vérification avant le jalon J4 conditionne la fiabilité de l'ensemble des projections présentées dans cette note.