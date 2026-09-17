# Note de cadrage — Projet IA NutriScope
### TP 8 · Jalon J2 · Version v0.2

**Équipe :** Sébastien HUS / Nicolas CUSUMANO
**Date :** 17/09/2026
**Rédigée par :** le chef de projet, à partir des travaux déjà co-construits par l'équipe : [note de cadrage initiale](annexes/note_cadrage.md), [cahier des charges](annexes/cahier_des_charges.md), [analyse des risques](annexes/opportunite.md), [étude de faisabilité](annexes/faisabilites.md), [qualification des données](annexes/donnees.md), [benchmark concurrentiel](annexes/benchmark.md), [note KPI, coûts et ROI](note_hypotheses_kpi_roi.md), [plan d'adoption](annexes/plan_adoption.md)
**Statut :** consolidée pour validation en revue de jalon (direction / formateur)

---

## Préambule

Après huit travaux pratiques de cadrage, d'exploration data, d'analyse de faisabilité et de chiffrage financier, cette note réunit dans un seul document ce qui doit désormais servir de référence unique au pilotage du projet : le besoin, le périmètre, les parties prenantes, les indicateurs de performance et de retour sur investissement, les risques avec leurs plans de mitigation, et le calendrier des prochains jalons (J3 à J7). Elle ne reformule pas les analyses détaillées déjà produites — elle les synthétise et les arbitre là où plusieurs versions coexistaient, pour qu'une seule ligne directrice reste opposable à l'équipe et à la direction.

Chaque document cité dans les pages qui suivent est accessible par un lien : les travaux antérieurs sont stockés au niveau racine du projet, et les trois documents produits en même temps que cette note se trouvent dans le même dossier (`claude/`).

---

## 1. Contexte et besoin

### 1.1 Le problème à résoudre

En magasin, un consommateur qui veut comparer deux produits alimentaires perd aujourd'hui plus d'une minute par produit : l'étiquette nutritionnelle est dense, le Nutri-Score n'est renseigné que sur 44,9 % des références commercialisées en France (constat établi lors de l'[exploration du jeu de données Open Food Facts](annexes/journal.md)), et aucun outil simple ne propose une alternative plus saine au moment même du choix. Cette charge mentale touche en priorité les parents qui gèrent les courses du foyer sous contrainte de temps — le persona central du projet, **[Sophie Martin](annexes/note_cadrage.md)**, 38 ans, assistante administrative, qui réalise ses courses deux à trois fois par semaine et doit arbitrer en rayon sans disposer d'une information fiable et immédiate.

### 1.2 Le besoin validé par la direction

Un [entretien semi-directif conduit avec la direction](annexes/recap_entretien.md) a confirmé que l'application attendue doit être intelligente, simple, personnalisée, fiable et accessible au plus grand nombre, sans jamais se substituer à un avis médical. La direction a validé Sophie Martin comme cible prioritaire du MVP (version minimale commercialisable) et a positionné quatre fonctionnalités comme indispensables dès la première version : la recherche et l'identification d'un produit (scan de code-barres ou recherche manuelle), une fiche produit synthétique compréhensible sans connaissance nutritionnelle, la comparaison de plusieurs produits, et un assistant conversationnel de recommandation. Les profils spécialisés — personnes diabétiques ou allergiques, sportifs, professionnels de santé — sont reconnus comme porteurs de valeur mais ne constituent pas la cible du MVP ; ils sont traités comme des évolutions.

### 1.3 La réponse produit

NutriScope répond à ce besoin par quatre briques d'intelligence artificielle complémentaires, orientées vers l'utilisateur final et spécifiées dans le [cahier des charges](annexes/cahier_des_charges.md) : un pipeline de nettoyage qui fiabilise la base Open Food Facts, un modèle prédictif de Nutri-Score qui comble les fiches incomplètes, un moteur de substitution qui propose des alternatives plus saines dans le même rayon, et un assistant conversationnel qui vulgarise l'information sans jamais inventer de réponse (fonctionnement dit RAG — retrieval-augmented generation : le système va chercher des documents pertinents avant de générer sa réponse, pour l'ancrer sur des sources vérifiées, plutôt que de laisser le modèle de langage répondre de mémoire). Deux briques purement techniques viennent fiabiliser ces quatre-là : une segmentation du catalogue, qui regroupe automatiquement les produits réellement comparables entre eux et donne ainsi au moteur de substitution son terrain de recherche ; et un classifieur qui reconnaît la catégorie d'un produit à partir de sa photo, utilisé en interne pour compléter le catalogue lorsque la catégorie est absente ou peu fiable. Aucune de ces deux briques n'est exposée à l'utilisateur comme une fonctionnalité en soi. Le positionnement reste strictement informatif : NutriScope aide à choisir, il ne diagnostique pas et ne remplace pas un professionnel de santé — un principe rappelé par la direction elle-même comme la ligne rouge du projet.

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

Cette cartographie prolonge celle établie dans la [note de cadrage initiale](annexes/note_cadrage.md). Deux arbitrages la structurent : le Marketing pèse davantage que son pouvoir formel ne le suggère, car la priorité des premiers mois est l'existence sur les stores ; à l'inverse, l'équipe data ne pourra peser sur les décisions produit qu'une fois une base d'utilisateurs suffisante constituée pour objectiver ses recommandations.

### 2.2 Suite donnée en aval : le plan d'adoption

Cette cartographie a été affinée dans un [plan d'adoption](annexes/plan_adoption.md) dédié, qui détaille pour onze acteurs (dont le support client, les trois profils d'utilisateurs et les financeurs) une action datée et nommée — jamais une intention générique de type « mieux communiquer ». Ce plan, aligné sur les jalons J5 à J7 du calendrier du §6, n'est pas repris intégralement ici : il reste la référence opérationnelle pour la conduite du changement et sera activé à l'approche du lancement public.

---

## 3. Périmètre

### 3.1 Ce qui est inclus dans le MVP

Le périmètre du MVP, arrêté dans le [document de périmètre](annexes/perimetre.md) puis détaillé dans le [cahier des charges](annexes/cahier_des_charges.md), est restreint à cinq à huit rayons alimentaires principaux de la grande distribution, pour garantir la précision du moteur de substitution avant toute extension. Il comprend :

- le pipeline automatisé d'ingestion et de nettoyage du catalogue Open Food Facts ;
- le scan de code-barres et la recherche textuelle instantanée d'un produit ;
- la fiche produit synthétique, avec Nutri-Score réel ou prédit et un indice de confiance affiché systématiquement ;
- la segmentation du catalogue en familles de produits réellement comparables, qui délimite le champ de recherche du moteur de substitution ;
- le moteur de substitution, qui propose une à trois alternatives plus saines dans la même catégorie ;
- l'assistant conversationnel RAG, adossé à un corpus constitué des fiches du catalogue et de sources publiques de référence en nutrition, dont la provenance et la licence sont tracées source par source ;
- la gestion explicite des cas d'incertitude (produit inconnu, données insuffisantes) ;
- le classifieur de catégorie de produit à partir d'une photo, brique technique interne qui complète le catalogue lorsque la catégorie manque — jamais affiché tel quel à l'utilisateur ;
- les tableaux de bord de suivi : l'un sur la qualité et la structure du catalogue, lisible sans compétence technique, l'autre sur l'exploitation de l'application (trafic, temps de réponse, taux d'erreur, coût cumulé du modèle de langage).

### 3.2 Ce qui est différé (évolutions V2 et V3)

L'historique des scans, la gestion des favoris et le profil utilisateur avec filtres d'allergènes sont classés en évolution V2 : ils demandent une base d'utilisateurs déjà active pour avoir du sens. La personnalisation avancée des recommandations selon un objectif nutritionnel du foyer est envisagée en V3.

### 3.3 Ce qui est explicitement hors périmètre

La reconnaissance visuelle d'étiquette par photographie (traitement dit de vision par ordinateur appliqué à la lecture d'une étiquette nutritionnelle) et le développement d'une application mobile native (développement spécifique pour iOS ou Android) sont exclus du périmètre du projet fil rouge. Le MVP est livré sous forme d'une API conteneurisée associée à un démonstrateur web, accessible aussi bien depuis un ordinateur que depuis le navigateur d'un téléphone — ce qui reste compatible avec un usage en rayon, en magasin. Cette exclusion porte uniquement sur le développement natif dédié ; elle ne préjuge pas d'une éventuelle version mobile native ultérieure, qui n'est à ce jour actée dans aucun document de cadrage, ni comme évolution V2 ni comme évolution V3.

Cette exclusion ne doit pas être confondue avec le classifieur de catégorie de produit du §3.1 : ce dernier est une brique interne qui travaille sur les photos déjà présentes dans le catalogue pour en déduire une catégorie, il ne demande à l'utilisateur ni de prendre une photo ni de lire une étiquette.

### 3.4 Contraintes encadrant le projet

Le projet s'exécute sous quatre familles de contraintes posées par la direction, non négociables à ce stade.

**De temps.** L'enveloppe totale est de 216 heures d'équipe réparties sur huit mois, cadencées par les sept jalons du §6. C'est cette enveloppe, et non l'ambition fonctionnelle, qui a dicté le resserrement du périmètre décrit plus haut.

**Techniques.** La pile est imposée : Python 3.12, un dépôt de code partagé par l'équipe, une base relationnelle PostgreSQL pour servir l'application et des fichiers Parquet interrogés par DuckDB pour l'analyse et l'apprentissage, scikit-learn pour les modèles statistiques, TensorFlow/Keras pour le classifieur d'images, FastAPI pour l'interface applicative, Docker pour la conteneurisation. Tout autre outil reste libre à condition d'être justifié par écrit.

**Réglementaires.** RGPD pour les données personnelles, règlement européen sur l'intelligence artificielle (AI Act) pour le positionnement du système, RGAA pour l'accessibilité numérique, et les licences des données sources — ODbL pour la base, CC-BY-SA pour les photographies — avec les obligations de crédit et de partage à l'identique qu'elles emportent (voir §5).

**De langue.** Le code et les noms de variables sont rédigés en anglais ; la documentation et les présentations, en français.

---

## 4. Indicateurs de performance et retour sur investissement

### 4.1 Les indicateurs de cadrage validés par la direction

Lors de l'[entretien de cadrage](annexes/recap_entretien.md), la direction a fixé quatre critères de succès pour le projet : 100 000 utilisateurs à terme, 33 % d'utilisateurs actifs mensuels, 40 % de fidélisation (réutilisation de l'application), et une note moyenne supérieure à 4,3 sur 5 sur les stores applicatifs. La [trajectoire d'acquisition](annexes/synthese_strategique_nutriscope.md) retenue pour le projet dépasse déjà largement le premier seuil dès le sixième mois (231 000 utilisateurs actifs mensuels projetés), ce qui déplace l'enjeu réel du projet de la seule acquisition vers la fidélisation et la rentabilité — les deux points que les indicateurs produit ci-dessous viennent surveiller de près.

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

Ces six indicateurs, leur baseline, leur responsable de suivi et leur lien avec les objectifs métier (fidéliser, monétiser, tenir les coûts, rassurer) sont détaillés dans l'[arbre des indicateurs NutriScope](https://claude.ai/artifact/2WDBdrS6KjEVzuRVHbcgsM) et dans la [note d'hypothèses KPI, coûts et ROI](annexes/note_hypotheses_kpi_roi.md).

### 4.3 Le coût du projet et son retour sur investissement

Le coût total de possession (TCO) du projet — calculé dans le [tableur de chiffrage](annexes/kpi_roi.xlsx) et documenté hypothèse par hypothèse dans la [note associée](annexes/note_hypotheses_kpi_roi.md) — est structuré en quatre familles : construction initiale, fonctionnement courant, accompagnement au changement et conformité réglementaire. Il s'établit à 260 154 € cumulés à douze mois, 554 269 € à vingt-quatre mois et 1 090 781 € à trente-six mois. Ce montant est identique dans les trois scénarios de revenus retenus : seul ce que le projet encaisse varie d'un scénario à l'autre, pas ce qu'il dépense.

Le modèle de revenus repose sur un abonnement Premium à 2,99 € par mois et sur des contrats de valorisation de données anonymisées auprès de distributeurs. Le taux de conversion vers l'abonnement Premium — arbitré avec la direction par prudence, en l'absence de tout test de vente réel — est le paramètre qui pèse le plus sur la rentabilité :

| Scénario | Taux de conversion Premium | ROI à 12 mois | ROI à 24 mois | ROI à 36 mois | Mois de rentabilité |
|---|---|---|---|---|---|
| Pessimiste | 0,7 % | −70,7 % | −28,2 % | −1,9 % | Jamais atteinte en 36 mois |
| Normal (central) | 1 % | −48,9 % | +11,3 % | +46,8 % | Mois 22 |
| Optimiste | 2 % | +6,8 % | +126,9 % | +196,8 % | Mois 12 |

**Lecture retenue pour le pilotage :** seul le scénario optimiste atteint l'équilibre dans la première année, et de justesse. Le scénario central le franchit au bout de vingt-deux mois, porté surtout par la croissance du nombre d'utilisateurs actifs plutôt que par le taux de conversion lui-même. Le scénario pessimiste, lui, ne l'atteint jamais sur les trois années observées : à 0,7 % de conversion, ce n'est pas l'horizon de rentabilité qui est en question, c'est la viabilité du modèle économique. Vérifier ce taux de conversion auprès d'utilisateurs réels — la cohorte de bêta-testeurs mobilisée avant le jalon J6, seule fenêtre où l'application existe et n'est pas encore ouverte au public — est donc la priorité absolue de validation économique du projet, avant même la maîtrise des coûts. Il faut être lucide sur ce que cette mesure vaudra : une cohorte d'une vingtaine à une trentaine de personnes ne permet pas d'estimer un taux de conversion avec précision. Elle permet en revanche de détecter un désintérêt franc pour l'offre payante — et c'est le seul signal qui compte à ce stade.

---

## 5. Risques et plans de mitigation

L'[analyse des risques](annexes/opportunite.md), complétée par la [qualification des sources de données](annexes/donnees.md) et l'[étude de faisabilité](annexes/faisabilites.md), distingue un risque critique et cinq risques importants, tous liés à la qualité, à la complétude ou à la disponibilité des données, à l'exception du risque réglementaire :

| Risque | Probabilité | Impact | Niveau | Plan de mitigation retenu |
|---|---|---|---|---|
| **R1 — Données nutritionnelles incohérentes** (valeurs de sucre ou de sel supérieures à 100 g, énergie négative) | Élevée | Élevé | 🔴 Critique | Exclusion des produits présentant des incohérences majeures des jeux d'entraînement et des calculs affichés à l'utilisateur ; conservation des données brutes à des fins d'audit uniquement. |
| **R2 — Produits incomplets** (ingrédients, Nutri-Score ou valeurs nutritionnelles manquants) | Élevée | Moyen | 🟠 Important | Analyse partielle autorisée lorsque les données critiques sont présentes, avec affichage systématique d'un indice de confiance plutôt qu'un rejet pur et simple. |
| **R3 — Hétérogénéité des formats de données** (pays, catégories, unités multiples) | Élevée | Moyen | 🟠 Important | Normalisation automatisée à l'import et constitution de référentiels internes, plutôt qu'une correction manuelle au cas par cas. |
| **R4 — Dépendance à la source unique Open Food Facts** | Moyenne | Élevé | 🟠 Important | Mise en cache locale des produits les plus consultés, synchronisation périodique, et architecture ouverte à l'intégration future d'autres sources (par exemple la table CIQUAL). |
| **R5 — Évolution de la réglementation sur les données sensibles** (allergies, préférences alimentaires) | Faible | Élevé | 🟠 Important | Minimisation des données collectées, consentement explicite, droit de modification et de suppression, politique de confidentialité transparente ; stockage local des données de santé sans centralisation nominative côté serveur. |
| **R6 — Recommandations peu pertinentes** (moteur de substitution ou assistant) | Moyenne | Élevé | 🟠 Important | Priorité aux règles métier explicables sur les modèles d'apprentissage tant que l'historique de données est insuffisant ; introduction progressive de modèles prédictifs après validation de leur qualité. |

La [matrice probabilité × impact](annexes/matrice-risques.jpg) associée classe ces risques selon une échelle à trois niveaux : rouge pour un plan de mitigation obligatoire avant tout passage en production, orange pour un plan à définir avant le jalon concerné, jaune pour un risque à surveiller sans action immédiate — aucun risque du projet ne se situe aujourd'hui dans cette dernière catégorie.

Deux risques complémentaires, de nature non technique, restent surveillés en aval de ce tableau : le risque de conflit d'intérêt lié aux partenariats de marques (mise en avant d'un produit partenaire dans une recommandation présentée comme neutre) et le risque de perte de confiance en cas d'erreur de l'assistant sur un allergène ou un profil diabétique — ce dernier étant considéré par la [direction](annexes/recap_entretien.md) comme le risque le plus grave que le projet puisse encourir, la réputation de l'application étant son actif le plus important.

Un risque complémentaire, propre à la brique de classification par photo introduite au §3.1, doit être surveillé : la couverture et la qualité des photos disponibles peuvent être hétérogènes selon les rayons, ce qui limiterait la fiabilité de la classification sur certaines catégories. La mitigation retenue reprend le principe déjà appliqué aux risques R2 et R3 : le résultat du classifieur reste un signal interne au catalogue, jamais affiché tel quel à l'utilisateur, et les catégories insuffisamment couvertes par les photos sont explicitement identifiées plutôt que masquées.

Deux risques supplémentaires, non couverts par le registre R1-R6, ont été identifiés en consolidant ce cadrage :

- **Obligations de licence sur les données sources.** La base Open Food Facts est distribuée sous licence ODbL (Open Database License) et ses photographies sous licence CC-BY-SA : leur usage impose de créditer Open Food Facts dans chaque livrable, et de repartager dans les mêmes conditions toute base construite à partir de la leur (clause dite de partage à l'identique). Deux actions en découlent avant le jalon J7 : afficher un crédit Open Food Facts visible dans l'application et dans chaque document livré (US-13) ; et faire confirmer par un regard juridique que la valorisation B2B envisagée au §4.3 — qui porte sur des indicateurs d'usage propres à NutriScope, pas sur une redistribution de la base Open Food Facts — reste bien hors du champ de cette clause.
- **Robustesse de l'assistant face aux tentatives de contournement.** Au-delà de la pertinence des réponses (R6), l'assistant doit résister aux tentatives explicites de le détourner de son rôle : demande de conseil médical déguisée, question hors sujet insistante, instruction dissimulée dans un message. La mitigation retenue est un prompt système explicite (rôle, ton, périmètre, consignes de refus) éprouvé par des tests contradictoires croisés entre équipes avant le jalon J5, puis figé — voir §6.
- **Biais des modèles.** Le modèle de Nutri-Score comme le classifieur d'images apprennent sur un catalogue dont la couverture est inégale selon les rayons et selon les marques. Leurs erreurs ne se répartiront donc pas uniformément, et rien ne garantit a priori qu'elles n'affectent pas davantage certaines familles de produits que d'autres — ce qui, sur un produit d'aide au choix alimentaire, se traduirait par des recommandations systématiquement moins fiables pour une partie des utilisateurs. La mitigation retenue est une analyse de biais conduite rayon par rayon et classe par classe, documentée au même titre que les performances et consolidée au jalon J7.

Six principes directeurs se dégagent de cette analyse et s'appliquent à l'ensemble du projet : la qualité prime sur la quantité de données conservées, la transparence est systématique dès qu'une information est incertaine, la normalisation des données est automatisée plutôt que manuelle, les dépendances externes sont réduites par la mise en cache et l'ouverture à d'autres sources, l'introduction de l'intelligence artificielle reste progressive et maîtrisée, et l'ensemble des indicateurs et modèles est réévalué en continu.

---

## 6. Macro-planning : des jalons J3 à J7

Le projet est structuré en sept jalons datés, validés avec la direction. Les jalons J1 (base de données opérationnelle, 1er septembre) et J2 (note de cadrage, backlog et plan de pilotage — ce jalon même) sont atteints à la clôture de ce TP8. Le calendrier ci-dessous couvre les cinq jalons restants ; son détail travaux par travaux figure dans le [plan de projet](planning.md).

| Jalon | Date | Objectif | Livrables |
|---|---|---|---|
| **J3** | 14 octobre | Socle data consolidé | Pipeline de données documenté, rapport d'analyse exploratoire, tableaux de bord de suivi de la qualité des données |
| **J4** | 4 novembre | Modèles d'intelligence artificielle évalués | Modèle prédictif de Nutri-Score, segmentation du catalogue, moteur de substitution, et classifieur de catégorie de produit à partir d'une photo — chacun avec ses métriques d'évaluation |
| **J5** | 30 novembre | Assistant conversationnel RAG validé | Assistant démontrable, garde-fous testés (y compris par des mises à l'épreuve croisées entre équipes), version figée avant intégration |
| **J6** | 29 décembre | Application stabilisée et déployée | API, interface de démonstration, conteneurisation et intégration continue, éprouvés en conditions d'autonomie d'équipe |
| **J7** | 14 janvier | Produit final et conformité | Documentation complète, analyse de biais consolidée, dossier de conformité (RGPD, AI Act, accessibilité RGAA, crédits des données sources), soutenance devant la direction |

Chaque jalon se matérialise par une étiquette de version dans le dépôt de code — v0.3 à J3, v0.4 à J4, v0.5 à J5, v1.0 à J6 — et par une démonstration de ce qui fonctionne réellement devant la direction, pas par un exposé.

Une étape n'apparaît pas dans ce tableau parce qu'elle ne constitue pas un jalon en soi, mais elle conditionne deux décisions importantes : entre les jalons J5 et J6, une cohorte de vingt à trente bêta-testeurs est mobilisée sur l'application avant son ouverture. C'est cette cohorte qui porte à la fois les premiers retours d'usage du plan d'adoption et le test de l'offre payante décrit au §4.3.

Le calendrier porte enfin une décision déjà arbitrée avec la direction : le [plan d'adoption](annexes/plan_adoption.md) — communiquer, accompagner, mesurer — s'active à partir du jalon J5 pour être pleinement déployé au jalon J7.

Le jalon J4 inclut le classifieur de catégorie de produit introduit au §1.3 et au §3.1 : il s'agit d'une brique technique interne, au service de la segmentation du catalogue et du moteur de substitution, et non d'une fonctionnalité exposée à l'utilisateur final. Son histoire est inscrite au [backlog produit](backlog_produit_tp8.md) (US-12) et son risque propre est traité au §5.

---

## 7. Synthèse

Le projet NutriScope dispose désormais d'un cadrage complet et cohérent : un besoin validé par la direction et centré sur un persona prioritaire clairement identifié, un périmètre MVP resserré sur cinq à huit rayons, quatre briques d'intelligence artificielle et deux briques techniques, des indicateurs de performance et un modèle de retour sur investissement chiffrés sur trois scénarios, une analyse des risques assortie de plans de mitigation retenus, et un calendrier détaillé jusqu'au jalon J7. Le [backlog produit](backlog_produit_tp8.md) outillé et priorisé, le [plan de projet](planning.md) et les [rituels d'équipe et l'outil de suivi](outillage_rituels_tp8.md) font l'objet des documents qui accompagnent cette note.

Le point de vigilance à porter à la connaissance de la direction lors de la revue de ce jalon reste le même que celui déjà identifié dans le chiffrage financier : la rentabilité du scénario central repose sur un taux de conversion Premium qui n'a encore jamais été testé auprès d'un utilisateur réel. Sa vérification auprès de la cohorte de bêta-testeurs, avant le jalon J6, conditionne la fiabilité de l'ensemble des projections présentées dans cette note.
