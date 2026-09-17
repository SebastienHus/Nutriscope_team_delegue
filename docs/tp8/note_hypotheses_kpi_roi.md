# TP 7 — Note d'hypothèses : KPI, coûts & ROI

**Projet :** NutriScope · **TP :** TP 7 « KPI, coûts & ROI » (Cahier des TP, p. 19) · **Date :** 15/09
**Objectif du TP :** chiffrer le projet comme le ferait une direction financière.
**Livrables associés :** `docs/cadrage/kpi_roi.xlsx` (tableur versionné, hypothèses apparentes), `trajectoire_36_mois_mensuelle_saisonniere_nutriscope.csv` (détail mensuel de la trajectoire MAU) et la présente note.

Cette note explicite les hypothèses et les résultats du tableur `kpi_roi.xlsx`. Toutes les valeurs d'entrée y figurent en **bleu sur fond jaune** (onglet *Hypotheses*) ; tout le reste est calculé par formule.

> **Sources.** Les définitions de méthode (§1) reprennent le support de cours, module 2.4. Les indices de saisonnalité (§5) s'appuient sur un indice de consommation alimentaire mensuelle (base 100). Ces sources ne sont pas re-citées à chaque usage dans la suite du document.

---

## 1. Rappels de cours

**Bon KPI :** mesurable, attribuable (à une équipe ou une décision précise), actionnable (un seuil franchi déclenche une action), compris de tous, peu nombreux (5 à 7 KPI produit maximum — c'est ce qui a guidé le choix des six KPI produit du §2).

**Arbre des indicateurs :** objectif business → KPI métier (ce que regarde la direction) → KPI produit (un indicateur d'usage par fonctionnalité) → métriques techniques (ce que l'équipe technique surveille au quotidien). Chaque flèche entre deux niveaux est une hypothèse à vérifier, pas une certitude : si la métrique technique s'améliore sans effet sur le KPI produit associé, l'hypothèse est fausse.

**Réglages d'un KPI :** Baseline (valeur de départ, souvent 0 pour un produit pas encore lancé), Cible (valeur visée, datée), Seuil d'alerte (valeur qui déclenche une action), Fréquence de mesure, Responsable du suivi.

---

## 2. KPI produit retenus

Six KPI produit ont été définis (le tableau complet, avec baseline, source de mesure et fréquence, est dans l'onglet *KPI* du tableur) :

| KPI | Cible | Seuil d'alerte |
|---|---|---|
| Scans par jour actif | ≥ 1,5 scan/jour actif à M6 | < 0,8 |
| Taux d'activation à J7 | ≥ 60 % à M6 | < 40 % |
| Rétention à 30 jours | ≥ 40 % à M12 | < 20 % |
| Taux de substitution acceptée | ≥ 15 % à M12 | < 8 % |
| Taux de réponses assistant sourcées | ≥ 90 % dès la mise en production | < 80 % |
| Coût par requête assistant | ≤ 0,02 € / conversation | > 0,03 € |

Le taux de substitution acceptée ci-dessus est un KPI produit : il mesure si l'utilisateur *choisit* la suggestion. Ce choix dépend d'une condition technique en amont, posée dans l'onglet *Hypotheses* (section I) du tableur : le moteur doit atteindre une **précision@3 d'au moins 85 % à 90 %**, c'est-à-dire qu'au moins une substitution pertinente doit figurer parmi les 3 premières proposées dans 85 à 90 % des cas — c'est la métrique technique T3 de l'arbre du §3, qui conditionne le KPI produit correspondant.

### Pourquoi chacun de ces seuils, et pas un autre

Les seuils d'alerte sont reliés à un raisonnement propre au projet NutriScope.

**Scans par jour actif < 0,8.** Le persona principal, Sophie Martin, fait ses courses environ une à deux fois par semaine, avec plusieurs produits comparés à chaque passage. En dessous de 0,8 scan par jour et par utilisateur actif en moyenne, on est sous le seuil d'une utilisation minimale à chaque session de courses : cela signale que l'application est ouverte sans être réellement utilisée en rayon, ce qui est le cœur de sa proposition de valeur.

**Taux d'activation à J7 < 40 %.** La fréquence de courses hebdomadaire de notre persona principal fixe la fenêtre de test naturelle : un nouvel inscrit doit avoir l'occasion de scanner au moins un produit dans la semaine qui suit son installation. Si moins de 4 personnes sur 10 le font, la majorité des inscrits n'atteint jamais le moment où l'application est censée prouver son utilité — ce n'est plus un problème de croissance, mais un problème de parcours d'accueil ou de proposition de valeur perçue.

**Rétention à 30 jours < 20 %.** Ce seuil est directement lié au modèle économique retenu (abonnement mensuel Premium) : un abonnement mensuel n'a de sens que si l'utilisateur revient d'un mois sur l'autre. En dessous de 20 % de rétention, plus de huit utilisateurs sur dix disparaissent en un mois — à ce niveau, il devient incohérent de vendre un abonnement mensuel à des gens qui n'utilisent plus l'application le mois suivant : c'est le modèle économique tout entier qui devient intenable, pas seulement un indicateur d'usage dégradé.

**Taux de substitution acceptée < 8 %.** Le moteur de substitution est présenté dans `benchmark.md` comme le principal élément différenciant de NutriScope face à Yuka ou Foodvisor. Si moins d'un utilisateur sur douze accepte une suggestion de substitution, cette fonctionnalité — pourtant citée comme un axe fort du cahier des charges (brique 3) — ne serait en réalité utilisée que par une minorité marginale, ce qui remettrait en cause l'argument différenciant du projet, pas seulement la performance d'un algorithme.

**Taux de réponses assistant sourcées < 80 %.** Le cahier des charges (exigence US-04) impose que l'assistant conversationnel s'appuie uniquement sur des données vérifiées, sans invention. En dessous de 80 %, une réponse sur cinq n'est plus appuyée sur une source identifiée : c'est le seuil à partir duquel un utilisateur attentif commencerait statistiquement à repérer des réponses douteuses, ce qui active directement le risque de perte de confiance déjà identifié dans `opportunite.md` (risque R6 : recommandations peu pertinentes).

**Coût par requête assistant > 0,03 €.** Ce seuil découle du modèle de coûts du tableur lui-même, pas d'un chiffre extérieur : avec les hypothèses retenues (4 000 jetons par conversation, 2 € par million de jetons), le coût actuel est d'environ 0,008 € par conversation. Au-delà de 0,03 € — soit environ quatre fois l'hypothèse posée — le poste « Run - modèle de langage » deviendrait le principal poste de coût variable et menacerait un modèle déjà fragile avec les taux de conversion retenus (1 % en scénario normal, voir §6).

### Quelles actions engager si le seuil est franchi

Un seuil d'alerte n'a d'intérêt que s'il déclenche une décision (voir §1, « actionnable ») : voici, pour chaque KPI, le diagnostic à poser en premier et l'action qui en découle.

**Scans par jour actif < 0,8.**
- Le temps de réponse de l'API de scan (métrique T1) s'est dégradé → améliorer les performances techniques bloquantes en priorité (optimisation de l'API, réduction de la latence de reconnaissance).
- L'abandon est concentré sur certains rayons (problème de reconnaissance produit plutôt que d'usage général) → même diagnostic que pour la substitution acceptée ci-dessous : resegmenter par rayon pour identifier les catégories de produits les moins bien couvertes par le modèle.
- Ni l'un ni l'autre : le geste de scan lui-même n'est pas en cause → revoir l'ergonomie du parcours (nombre d'étapes, clarté des premiers écrans sur où et quand scanner).

**Taux d'activation à J7 < 40 %.**
- Simplifier l'ergonomie du parcours d'accueil (réduire le nombre d'étapes avant le premier scan, clarifier l'invitation à essayer).
- Mettre en place un contrôle technique automatique qui détecte les refus de permission caméra et les erreurs d'installation, pour savoir quelle part du décrochage leur est imputable avant d'agir sur l'ergonomie.
- Tester une relance (notification ou e-mail) à J2-J3 pour les inscrits n'ayant pas encore scanné.

**Rétention à 30 jours < 20 %.**
- Analyse de cohortes pour situer le moment exact du décrochage (dès la deuxième semaine, ou plus tard).
- Notifications de rappel contextualisées (nouveaux rayons couverts, substitutions proposées).
- Retour direct in-app auprès des utilisateurs inactifs depuis 15 jours, pour comprendre le frein réel avant de pousser l'abonnement payant plus fort.

**Taux de substitution acceptée < 8 %.**
- La métrique technique associée (précision@3, seuil ≥ 85-90 %, voir §3) est en dessous du seuil → le problème est la qualité des suggestions elles-mêmes : réentraîner le moteur de substitution.
- La précision est correcte mais le taux d'acceptation reste bas → recueillir le motif de refus à chaque suggestion écartée (pourquoi elle ne convenait pas), et resegmenter par rayon pour repérer les catégories de produits les moins bien couvertes — c'est le même diagnostic « par rayon » qu'au point 1.

**Taux de réponses assistant sourcées < 80 %.**
- Auditer les thématiques de questions qui reviennent le plus parmi les réponses non sourcées, pour cibler en priorité l'enrichissement du corpus documentaire sur ces sujets.
- Une fois le corpus réentraîné et le taux redressé, envisager d'offrir quelques mois d'abonnement payant gratuits aux utilisateurs concernés, en geste commercial pour la gêne occasionnée.

**Coût par requête assistant > 0,03 €.**
- Identifier si la hausse vient du volume de jetons par conversation (contexte transmis au modèle trop long) ou du nombre de conversations par utilisateur.
- Réduire le contexte envoyé au modèle au strict nécessaire.
- Mettre en cache les réponses aux questions les plus fréquentes.
- Réserver le modèle actuel (le plus coûteux) aux comptes payants, et orienter les comptes gratuits vers un traitement moins coûteux.
- Constituer une base de questions-réponses préétablies sur les thématiques les plus demandées, pour répondre à ces cas sans solliciter le modèle à chaque fois.

---

## 3. Arbre des indicateurs NutriScope

Ce tableau est la donnée source du schéma publié séparément (voir lien ci-dessous) : il applique la grille de lecture du §1 (objectif business → KPI métier → KPI produit → métriques techniques) au projet NutriScope, avec pour chaque case sa baseline, sa cible, qui en assure le suivi, et — pour les KPI produit et les métriques techniques — à quoi il sert et ce qu'il montre.

**Schéma :** [Arbre des indicateurs NutriScope](https://claude.ai/artifact/2WDBdrS6KjEVzuRVHbcgsM) — même contenu que le tableau ci-dessous, mis en scène comme la page 28 du module 2.4. Pour le régénérer après une modification du tableau, republier la même page.

| Niveau | Indicateur | Rattaché à | Baseline | Cible | Responsable du suivi | Ce qu'il montre / à quoi il sert |
|---|---|---|---|---|---|---|
| Objectif business | NutriScope — adoption durable et rentabilité | — | — | Rentable au plus tard à M36 (voir §7) | Direction | Le pourquoi du projet : pas un chiffre à suivre au quotidien, mais ce que les quatre KPI métier ci-dessous sont censés faire avancer. |
| KPI métier | Fidéliser (rétention à 30 jours) | Objectif business | 0 % (aucun utilisateur avant le lancement) | ≥ 40 % à M12 | Responsable produit | Indique si le modèle d'abonnement mensuel est viable : sans retour régulier, l'objectif de rentabilité ne peut pas être atteint. |
| KPI métier | Monétiser (conversion Premium) | Objectif business | 0 % (pas d'offre payante avant le lancement) | 1 % en scénario central à M12 (voir §6) | Direction | Le levier qui pèse le plus sur le ROI (voir §7) : c'est lui qui décide si le projet atteint l'équilibre au mois 12 ou ne l'atteint pas du tout en trois ans. |
| KPI métier | Tenir les coûts (coût par utilisateur actif) | Objectif business | ≈ 0,03 €/mois, estimé à partir des hypothèses de coûts posées au §4 | ≤ 0,10 €/mois | Responsable infrastructure | Vérifie que le coût du Run ne dérive pas plus vite que la base d'utilisateurs ne grandit. |
| KPI métier | Rassurer (note moyenne sur les stores) | Objectif business | Non mesurable avant publication | ≥ 4,3/5 | Responsable produit | Indicateur de confiance perçue, en aval des exigences de fiabilité de l'assistant (P5, T4) et du moteur de substitution (P3, T3). |
| KPI produit | Scans par jour actif | Fidéliser | 0 (nouvel usage) | ≥ 1,5 à M6 | Responsable produit | **Sert à** vérifier que le scan de produit en rayon — la fonctionnalité cœur — est réellement utilisé, pas seulement l'application installée. **Montre** la fréquence d'usage réelle en situation de courses, rapportée aux utilisateurs actifs. |
| KPI produit | Activation à J7 | Fidéliser | 0 (nouvel usage) | ≥ 60 % à M6 | Croissance | **Sert à** repérer si le parcours d'accueil convertit l'inscription en usage réel dans la semaine qui suit. **Montre** la part des nouveaux inscrits ayant scanné au moins un produit dans les 7 jours suivant l'installation. |
| KPI produit | Rétention à 30 jours | Fidéliser | 0 % (aucun utilisateur avant le lancement) | ≥ 40 % à M12 | Responsable produit | **Sert à** mesurer directement ce que le KPI métier « Fidéliser » vise à faire bouger — c'est la même mesure, suivie au niveau produit. **Montre** la part des utilisateurs actifs à un mois donné qui reviennent le mois suivant. |
| KPI produit | Substitution acceptée | Monétiser | 0 (fonctionnalité neuve) | ≥ 15 % à M12 | Responsable data / IA | **Sert à** vérifier que la fonctionnalité différenciante du projet crée une valeur perçue, pas seulement une performance technique. **Montre** la part des suggestions de substitution proposées que l'utilisateur choisit réellement d'adopter. |
| KPI produit | Coût par requête assistant | Tenir les coûts | ≈ 0,008 €/conversation | ≤ 0,02 € / conversation | Responsable infrastructure | **Sert à** garder l'assistant conversationnel économiquement soutenable face au volume d'usage. **Montre** le coût variable réel (jetons du modèle de langage) par échange avec l'assistant. |
| KPI produit | Réponses assistant sourcées | Rassurer | Mesurée sur le jeu de test interne avant mise en production | ≥ 90 % dès la mise en production | Responsable data / IA | **Sert à** vérifier que l'assistant respecte l'exigence US-04 (pas d'invention) et donc la confiance des utilisateurs. **Montre** la part des réponses de l'assistant appuyées sur une source de données vérifiée. |
| Métrique technique | Temps de réponse API | Scans par jour actif | Mesurée en environnement de test avant mise en production | < 500 ms (exigence US-01) | Responsable infrastructure | **Sert à** garantir que le scan reste fluide en rayon, condition technique de P1. **Montre** le temps de réponse de l'API de scan et d'identification du produit. |
| Métrique technique | Disponibilité API | Activation à J7 | Objectif contractuel dès la mise en production | ≥ 99,5 % | Responsable infrastructure | **Sert à** éviter qu'une panne technique casse la confiance dès les premières utilisations, condition technique de P2. **Montre** la part du temps où l'API répond normalement. |
| Métrique technique | Précision du moteur de substitution (précision@3) | Substitution acceptée | Mesurée sur le jeu de test interne (hors ligne) avant mise en production | ≥ 85 à 90 % | Responsable data / IA | **Sert à** garantir que les 3 premières suggestions du moteur sont pertinentes, condition technique de P3. **Montre** la part des cas où au moins une substitution pertinente figure parmi les 3 premières proposées. |
| Métrique technique | Exactitude du Nutri-Score prédit | Substitution acceptée | Mesurée sur le jeu de test interne (hors ligne) avant mise en production | ≥ 85 % prédit correctement | Responsable data / IA | **Sert à** garantir la fiabilité de l'information affichée, condition de la confiance globale dans l'application. **Montre** la part des scores Nutri-Score prédits par le modèle qui correspondent au score réel du produit. |
| Métrique technique | Jetons consommés et prix du modèle | Coût par requête assistant | Hypothèse de calcul posée au §4 (4 000 jetons, 2 €/million de jetons) | À comparer à la consommation réelle dès M1 | Responsable infrastructure | **Sert à** piloter le poste de coût variable le plus sensible à la croissance du MAU. **Montre** le volume de jetons consommés par conversation et son coût, à comparer à l'hypothèse du §4. |
| Métrique technique | Latence P95 de l'assistant | Réponses assistant sourcées | Mesurée en test de charge avant mise en production | < 3 s | Responsable infrastructure | **Sert à** détecter les lenteurs qui touchent une minorité d'utilisateurs mais dégradent leur expérience. **Montre** le temps de réponse en dessous duquel se situent 95 % des requêtes adressées à l'assistant. |
| Métrique technique | Couverture documentaire de l'assistant | Réponses assistant sourcées | À définir en test | À définir en test | Responsable data / IA | **Sert à** savoir si l'assistant dispose d'assez de documents sourcés pour répondre sans extrapoler, condition technique de P5. **Montre** la part des questions posées pour lesquelles le mécanisme de récupération documentaire (le RAG : on va chercher des documents pertinents avant que le modèle de langage ne rédige sa réponse, pour l'ancrer sur des sources vérifiées) retrouve au moins un document pertinent. |

---

## 4. Hypothèses de coûts sur 12 mois

Le TCO est structuré selon les quatre familles vues au module 2.4 (Build / Run / Change / Conformité), avec un principe simple : **le Build est ponctuel, le Run + Change + Conformité reviennent chaque mois** et sont proportionnels au MAU du mois lorsque c'est pertinent (hébergement, coût du modèle de langage, stockage).

| Poste | Hypothèse | Base |
|---|---|---|
| **Build** — équipe technique | 3 profils à temps plein équivalent, coût chargé 58 000 €/an, mobilisés 7 mois | Dimensionnement du projet, détaillé ci-dessous |
| **Build** — données | 30 jours-homme à 500 €/jour (nettoyage, jeux de test, annotation) | Décomposition ci-dessous |
| **Run** — hébergement | 0,12 €/MAU actif/an (API + base + interface) | Ordre de grandeur module 2.4, remis à l'échelle du MAU réel du projet |
| **Run** — modèle de langage (assistant) | 10 % des MAU utilisent l'assistant/mois, 3 conversations/utilisateur, 4 000 jetons/conversation, 2 €/million de jetons | Méthode de calcul du module 2.4 |
| **Run** — stockage | 0,015 €/MAU actif/an (images, mémoire des substitutions déjà calculées) | Hypothèse interne |
| **Run** — supervision et réentraînement | 0,3 personne à temps plein équivalent | Hypothèse interne |
| **Build** — briques complémentaires | 38 jours-homme à 500 €/jour (classifieur d'images, segmentation du catalogue, tableau de bord qualité, mise en place de la supervision) + 500 € de calcul d'entraînement | Décomposition ci-dessous |
| **Run** — journalisation et surveillance | 0,010 €/MAU actif/an (collecte et conservation des journaux, alerte) | Hypothèse interne |
| **Change** — acquisition | 40 000 €/an (communication, référencement, contenu) | **Hypothèse fragile, voir §8** |
| **Change** — accompagnement | 8 000 €/an | Hypothèse interne |
| **Conformité** | 12 jours-homme à 500 €/jour (RGPD, mentions, audit de l'assistant) | Décomposition ci-dessous |

**Qui sont les « 3 profils » du Build, et d'où vient 58 000 €/an ?** Ce ne sont pas des personnes nommées : c'est une hypothèse de dimensionnement, construite à partir des 7 premiers mois du planning du projet (`note_cadrage.md`, §5), qui couvrent des travaux de nature différente. On retient 3 profils type plutôt qu'un seul poste générique : un profil données & modèle (pipeline de nettoyage, base SQL, modèle Nutri-Score — mois 1 à 3), un profil IA produit (moteur de substitution, assistant RAG — mois 4 et 5), et un profil intégration (API FastAPI, conteneurisation, déploiement — mois 6 et 7). Le coût chargé de 58 000 €/an n'est tiré d'aucun document du projet : c'est une hypothèse de marché, un ordre de grandeur courant en France pour un profil data/dev junior à confirmé, charges sociales comprises.

**D'où viennent les 30 jours-homme de données, et le tarif de 500 €/jour ?** Les 30 jours se décomposent ainsi : environ 10 jours de nettoyage et de qualification du jeu de données Open Food Facts, 10 jours de constitution des jeux de test (entraînement/validation du modèle Nutri-Score et du moteur de substitution), et 10 jours d'annotation manuelle pour évaluer la qualité des prédictions. Le tarif de 500 €/jour est une hypothèse de TJM (taux journalier moyen) : il se situe dans la fourchette basse à médiane observée en France pour un profil data/IA en freelance ou en stage renforcé (l'ordre de grandeur généralement cité va de 400 à 550 €/jour selon l'expérience et la localisation). Le même tarif est repris pour les 12 jours-homme de conformité, décomposés en environ 4 jours de registre RGPD (documentation des traitements), 4 jours de mentions légales et information utilisateur, et 4 jours d'audit du fonctionnement de l'assistant IA (traçabilité, biais, positionnement AI Act).

**D'où viennent les 38 jours-homme de briques complémentaires ?** Ils couvrent quatre travaux que le périmètre du projet comprend : environ 15 jours pour le classifieur de catégorie de produit à partir d'une photo (préparation du jeu d'images, entraînement d'un modèle de référence puis d'un modèle par transfert d'apprentissage, évaluation classe par classe), 5 jours pour la segmentation du catalogue, 8 jours pour le tableau de bord de qualité du catalogue et 10 jours pour la mise en place de la supervision et du tableau de bord d'exploitation. Le jeu de photographies d'entraînement étant mis à disposition, aucun coût d'acquisition de données n'est retenu : seul le calcul d'entraînement l'est, sous forme d'un forfait de 500 € couvrant la location de matériel de calcul le temps des essais. Ces jours-homme sont valorisés au même tarif journalier que les autres postes de construction et étalés sur la même durée de mobilisation d'équipe, par cohérence avec le reste du modèle — dans le calendrier réel, la mise en place de la supervision intervient plus tard que les autres.

**TCO Année 1 (mois 1 à 12) : 260 154 €**, calculé mois par mois par formule (le Build est concentré sur les 7 premiers mois, le Run est recalculé chaque mois à partir de la trajectoire MAU détaillée au §5).

Ces coûts sont **volontairement identiques dans les trois scénarios** — c'est la méthode enseignée au module 2.4 : seul ce qu'on encaisse change d'un scénario à l'autre, pas ce qu'on dépense.

---

## 5. Trajectoire MAU mensuelle : une hypothèse de saisonnalité

La trajectoire du TP1 (`trajectoire_36_mois_nutriscope.csv`) ne donne que 7 points de repère, espacés de 6 mois, reliés jusqu'ici par une simple droite. Pour un usage de courses alimentaires, ce n'est pas réaliste : l'usage varie selon les périodes de l'année. On a donc ajouté des **pics et des creux de progression** autour de cette trajectoire, sans jamais déplacer les 7 points de repère officiels.

**Hypothèse de calendrier.** Aucun document de cadrage ne fixe de date calendaire pour le Mois 1 de cette trajectoire (c'est un mois « 1 » relatif au lancement, pas une date réelle). On pose donc par hypothèse que le Mois 1 correspond au lancement public de l'application, fixé par convention à **novembre 2026** — cohérent avec l'objectif SMART « version publique sous 4 mois » à partir d'un démarrage de projet posé en septembre 2026 (`note_cadrage.md`). Avec cette convention, le Mois 12 tombe en octobre 2027, le Mois 36 en octobre 2029.

**Indices de saisonnalité retenus**, dérivés d'un indice de consommation alimentaire mensuelle (base 100 = mois moyen) :

| Mois | Indice de consommation | Variation retenue | Justification |
|---|---|---|---|
| Janvier | 110 | **+10 %** | Hausse liée aux régimes et à la remise en forme après les fêtes. |
| Février | 95 | **−5 %** | Consommation en retrait, creux hors période de fêtes. |
| Mars | 95 | **−5 %** | Consommation en retrait, avant la reprise liée à Pâques. |
| Avril | 105 | **+5 %** | Effet Pâques (chocolats, produits festifs). |
| Mai | 105 | **+5 %** | Consommation légèrement supérieure à la moyenne annuelle. |
| Juin | 100 | 0 % | Mois de référence. |
| Juillet | 115 | **+15 %** | Hausse des boissons, glaces et produits d'extérieur (grillades, pique-nique). |
| Août | 115 | **+15 %** | Cœur des vacances d'été : boissons, glaces, produits d'extérieur. |
| Septembre | 95 | **−5 %** | Rentrée : consommation en retrait par rapport à la moyenne annuelle. |
| Octobre | 100 | 0 % | Mois de référence. |
| Novembre | 100 | 0 % | Mois de référence. |
| Décembre | 125 | **+25 %** | Forte hausse des achats alimentaires liée aux fêtes de fin d'année. |

**Méthode de calcul.** Entre deux points de repère, on ne trace plus une droite mais on ajuste la vitesse de croissance mois par mois : l'augmentation de MAU d'un mois donné est multipliée par l'indice saisonnier du mois correspondant, puis l'ensemble des augmentations du segment est ramené (par un facteur de correction unique et automatique, voir ci-dessous) à retomber exactement sur le point de repère suivant. Concrètement, la croissance accélère nettement en décembre, ralentit en février-mars et en septembre, puis réaccélère en juillet-août, sans jamais faire baisser le nombre d'utilisateurs actifs d'un mois sur l'autre.

**Sur la colonne « Facteur de recalage (segment) » du tableur : ce que c'est, à quoi ça sert, comment c'est déterminé.** Prenons le segment avril 2027 → octobre 2027 (jalons du TP1 : 231 000 → 654 000 MAU, soit +423 000 sur 6 mois) pour dérouler le calcul :

1. **Incrément linéaire** (colonne G) : sans saisonnalité, chaque mois gagnerait 423 000 ÷ 6 = 70 500 MAU.
2. **Incrément brut ajusté** (colonne I) : on multiplie ces 70 500 par l'indice de saisonnalité du mois (§5 ci-dessus) — mai (+5 %) → 74 025, juin (0 %) → 70 500, juillet (+15 %) → 81 075, août (+15 %) → 81 075, septembre (−5 %) → 66 975, octobre → 70 500. Somme des 6 mois : 444 150, soit 21 150 de trop par rapport aux 423 000 attendus, parce que les indices retenus sur ce segment sont en moyenne légèrement positifs.
3. **Facteur de recalage** (colonne J) : le rapport entre ce qu'il faut vraiment atteindre et ce que donne la somme brute : 423 000 ÷ 444 150 ≈ **0,952** (soit environ −4,8 %). Ce facteur unique par segment est calculé automatiquement par la formule (jamais saisi à la main) et appliqué à chacun des 6 mois du segment.
4. **MAU retenu** (colonne K) : chaque incrément brut est multiplié par ce facteur avant d'être ajouté au mois précédent — mai devient 74 025 × 0,952 ≈ 70 500, juillet devient 81 075 × 0,952 ≈ 77 200, etc. La somme retombe alors exactement sur 654 000 en octobre, tout en gardant la forme saisonnière voulue (plus de croissance en juillet-août, moins en septembre).

En résumé, le facteur de recalage ne porte aucune information en lui-même : c'est un simple ajustement technique qui garantit que l'ajout d'indices saisonniers ne fait jamais dévier la trajectoire des 7 jalons officiels du TP1. Pour savoir **ce qui pousse le MAU à la hausse ou à la baisse un mois donné**, c'est la colonne juste à côté qu'il faut lire : **« Ce qui influence la hausse/la baisse ce mois-ci »** (et la colonne `explication` du CSV), qui traduit en une phrase l'indice saisonnier appliqué ce mois-là et sa justification.

**À quoi sert le fichier `trajectoire_36_mois_mensuelle_saisonniere_nutriscope.csv`.** Ce n'est pas une source d'hypothèse supplémentaire ni un second calcul indépendant : c'est un **export en texte simple** des colonnes de l'onglet *MAU_mensuel* du tableur (mois, année, mois calendaire, type, indice saisonnier, MAU retenu, explication). Il sert à consulter ou retraiter la trajectoire sans ouvrir Excel. Le tableur reste la seule source de vérité : si une hypothèse change dans `kpi_roi.xlsx`, ce fichier doit être régénéré pour rester à jour.

Le détail des 36 mois (formules dans l'onglet *MAU_mensuel* du tableur, valeurs calculées dans le CSV) : au Mois 12, la trajectoire ajustée retombe bien sur 654 000 MAU comme prévu au TP1, après un pic de croissance en décembre (environ +50 800 utilisateurs ce mois-là, contre +43 060 en rythme linéaire sur ce premier segment) et une nouvelle accélération en juillet-août (environ +77 200 par mois, contre +70 500 en rythme linéaire sur ce second segment).

---

## 6. Hypothèses de revenus (modèle choisi au TP6)

Le modèle économique reprend celui déjà posé dans `benchmark.md` et chiffré dans `synthese_strategique_nutriscope.md` : **abonnement gratuit/payant grand public + contrats B2B avec des distributeurs**.

| Levier | Pessimiste | Normal (central) | Optimiste |
|---|---|---|---|
| Taux de conversion vers l'abonnement Premium (2,99 €/mois) | **0,7 %** | **1 %** | **2 %** |
| Contrats B2B actifs (12 000 €/an chacun) | 0 | 2 | 5 |

Ces taux de conversion ont été arbitrés avec la direction, par prudence : à 1 % de conversion (scénario normal), c'est un ordre de grandeur nettement plus bas que les taux de conversion premium habituellement cités pour des applications grand public gratuites.

Le revenu de l'abonnement est calculé chaque mois comme `MAU du mois × taux de conversion × 2,99 €`, à partir de la même trajectoire MAU détaillée au §5.

---

## 7. Calcul de ROI sur trois scénarios

*(TCO identique dans les trois scénarios : 260 154 € cumulés à M12 / 554 269 € à M24 / 1 090 781 € à M36)*

| Scénario | Revenus M12 | ROI M12 | ROI M24 | ROI M36 | Mois de rentabilité |
|---|---|---|---|---|---|
| **Pessimiste** | 76 235 € | **−70,7 %** | −28,2 % | −1,9 % | non atteinte sur 36 mois |
| **Normal (central)** | 132 907 € | **−48,9 %** | +11,3 % | +46,8 % | mois 22 |
| **Optimiste** | 277 814 € | **+6,8 %** | +126,9 % | +196,8 % | mois 12 |

*(Le détail mensuel et la courbe des cumuls coûts/revenus sur 36 mois sont dans l'onglet ROI du tableur.)*

**Lecture.** **Seul le scénario optimiste atteint l'équilibre dans la première année, et tout juste** — au mois 12. Le scénario central ne le franchit qu'au bout de 22 mois, porté davantage par la croissance du nombre d'utilisateurs actifs que par le taux de conversion lui-même. Le scénario pessimiste, lui, **n'atteint jamais l'équilibre dans l'horizon de trois ans observé** : il en reste à −1,9 % au mois 36, c'est-à-dire qu'il en approche sans y parvenir.

Ce dernier point mérite d'être dit à la direction sans le lisser : le scénario pessimiste ne dispose d'aucune marge. Un écart de coûts de l'ordre de 10 % suffit à le faire passer d'un équilibre atteint de justesse en fin de troisième année à un équilibre jamais atteint. Autrement dit, à 0,7 % de conversion, ce n'est pas le calendrier de rentabilité qui est en cause, c'est le modèle économique lui-même. Cela confirme que **le taux de conversion Premium est le paramètre le plus déterminant du modèle**, avant même le montant des coûts — et que la fourchette basse retenue par prudence décrit un projet qui ne tient pas.

---

## 8. Les trois hypothèses les plus fragiles

| Hypothèse | Pourquoi elle est fragile | Comment la vérifier tôt |
|---|---|---|
| **Taux de conversion Premium (0,7 % à 2 %, arbitré en direction)** | Aucun essai réel de vente de l'abonnement n'a encore été mené ; c'est une hypothèse prudente, sans donnée d'usage pour la confirmer. C'est le levier qui fait le plus varier le résultat : le ROI à 12 mois passe de −70,7 % à +6,8 % selon ce seul paramètre, et c'est lui qui décide si le projet atteint l'équilibre dès le mois 12 ou ne l'atteint jamais dans l'horizon de trois ans. | Présenter l'offre payante (description de l'abonnement et bouton d'inscription, sans encaissement réel) à un groupe test de 200 à 300 utilisateurs avant le lancement public, et mesurer le taux d'intérêt réel plutôt que de continuer à deviner. |
| **Nombre et vitesse de signature des contrats B2B** | Aucun distributeur n'est engagé à ce jour ; le cycle de vente B2B (juridique, RGPD, intégration technique) est long et n'a jamais été mené par l'équipe. Cela représente jusqu'à 60 000 € de revenus en scénario optimiste, une part significative des revenus de l'Année 1. | Prendre contact avec 3 à 5 distributeurs ou enseignes cibles dès le mois 2 pour valider l'intérêt et le montant, avant de l'inscrire au budget comme un revenu acquis. |
| **Budget d'acquisition (40 000 €/an) et sa capacité à produire la trajectoire MAU (654 000 à M12)** | La trajectoire du TP1 est un objectif, pas une donnée observée : elle suppose un coût d'acquisition par utilisateur qui n'a jamais été mesuré en conditions réelles. Si ce coût réel est plus élevé que prévu, soit le budget de communication doit augmenter, soit la trajectoire MAU — et donc l'ensemble des revenus — ne se réalise pas. | Suivre le coût d'acquisition réel dès les premières campagnes test (mois 1-2) et le comparer à l'hypothèse implicite ; recalculer la trajectoire si l'écart dépasse 20 %. |

---

## Limites de l'exercice

Ce modèle est un exercice de chiffrage à hypothèses explicites, pas une comptabilité réelle : chaque montant est une estimation d'ordre de grandeur, volontairement documentée plutôt que dissimulée dans une formule. Il est construit pour être discuté et recalculé — toute cellule bleue de l'onglet *Hypotheses* du tableur peut être changée, et l'ensemble des feuilles (trajectoire MAU, coûts, revenus, ROI) se recalcule automatiquement. Le message principal à retenir pour la suite du projet est que **la rentabilité du scénario normal dépend d'une hypothèse encore jamais testée** (le taux de conversion Premium) : c'est elle qu'il faut vérifier en priorité avant le jalon J4, conformément à la consigne du TP7.
