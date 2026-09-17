# Backlog produit — Projet IA NutriScope
### TP 8 · Jalon J2 · Version v0.2

**Équipe :** Sébastien HUS / Nicolas CUSUMANO
**Date :** 17/09/2026

---

## Méthode de priorisation et d'estimation

Le backlog reprend l'ensemble des besoins déjà spécifiés dans le cahier des charges, formulés en histoires utilisateur (user stories) au format « En tant que…, je veux…, afin de… », complétées de leurs critères d'acceptation. Chaque histoire est priorisée selon la méthode MoSCoW (Must have : indispensable au MVP : Should have : fortement souhaitable mais différable : Could have : envisageable si le temps le permet : Won't have : explicitement écarté pour cette version) et estimée grossièrement en points d'effort (une échelle relative — non une durée en heures — qui reflète la taille et l'incertitude d'une histoire ; l'échelle retenue est 2, 3, 5, 8 ou 13 points, du plus simple au plus incertain).

L'estimation reste volontairement approximative à ce stade : elle sert à comparer les histoires entre elles et à vérifier que la charge du MVP reste cohérente avec les 216 heures allouées au projet fil rouge, pas à produire un engagement de délai ferme.

---

## Must have — indispensables au MVP

### US-01 — Scan et recherche de produit
**En tant que** Sophie, parent pressé faisant ses courses, **je veux** scanner le code-barres d'un produit en magasin ou saisir son nom dans la barre de recherche, **afin de** accéder instantanément à sa fiche d'analyse nutritionnelle sans perdre de temps en rayon.

*Critères d'acceptation :* le temps de réponse de l'interface pour retourner la fiche produit est inférieur à 500 millisecondes ; si le code-barres est absent du catalogue, un message clair informe l'utilisateur sans provoquer d'erreur bloquante.

**Priorité : Must have — Estimation : 5 points**

### US-02 — Transparence et Nutri-Score prédit
**En tant qu'** utilisateur soucieux de sa santé, **je veux** voir la fiche nutritionnelle simplifiée du produit et connaître son Nutri-Score, réel ou prédit par le modèle, **afin de** comprendre rapidement la qualité du produit même si l'étiquette d'origine est incomplète.

*Critères d'acceptation :* si le Nutri-Score d'origine est manquant, la valeur prédite est affichée avec une mention explicite ; un indice de confiance est systématiquement affiché ; l'explication des points forts et faibles est rédigée dans un langage pédagogique et non culpabilisant.

**Priorité : Must have — Estimation : 8 points**

### US-03 — Recommandation d'alternatives (substitution)
**En tant que** consommateur cherchant de meilleurs choix, **je veux** obtenir une à trois propositions d'alternatives plus saines équivalentes dans le même rayon, **afin de** remplacer facilement un produit mal noté par un autre mieux équilibré.

*Critères d'acceptation :* les alternatives suggérées appartiennent strictement à la même catégorie ou sous-catégorie de produit ; les produits recommandés présentent un Nutri-Score strictement meilleur que le produit scanné.

**Priorité : Must have — Estimation : 8 points**

### US-04 — Assistant nutritionnel conversationnel
**En tant qu'** utilisateur se posant des questions sur la composition d'un produit, **je veux** poser une question en langage naturel sur le produit scanné, **afin d'** obtenir une réponse synthétique, vérifiée et facile à comprendre.

*Critères d'acceptation :* l'assistant s'appuie uniquement sur des données factuelles vérifiées, sans invention ; les réponses intègrent un rappel de l'absence de conseil médical direct.

**Priorité : Must have — Estimation : 13 points**

### US-05 — Pipeline automatisé d'ingestion et de nettoyage
**En tant que** responsable des données, **je veux** exécuter un pipeline de nettoyage rejouable sur le catalogue Open Food Facts, **afin de** filtrer les doublons, éliminer les valeurs aberrantes et structurer la base d'analyse.

*Critères d'acceptation :* le script d'ingestion s'exécute de manière automatisée ; les données corrompues ou invalides sont isolées et journalisées dans un rapport d'audit.

**Priorité : Must have — Estimation : 8 points**

### US-06 — Gestion des produits inconnus et des incertitudes
**En tant qu'** utilisateur scannant un produit non répertorié ou très incomplet, **je veux** être informé clairement si le produit est inconnu ou si la fiabilité de la prédiction est trop faible, **afin de** ne pas recevoir d'information erronée ou de prédiction trompeuse.

*Critères d'acceptation :* si la confiance du modèle est inférieure à 50 %, l'application affiche « données insuffisantes pour estimer le score » plutôt qu'une prédiction incertaine ; l'utilisateur peut signaler un produit manquant ou une incohérence.

**Priorité : Must have — Estimation : 3 points**

### US-07 — Détail explicatif de l'indice de confiance
**En tant qu'** utilisateur souhaitant vérifier l'origine d'un résultat, **je veux** consulter le détail du calcul en cliquant sur l'indice de confiance, **afin de** comprendre quelles données ont servi au calcul.

*Critères d'acceptation :* un volet explicatif liste clairement les nutriments renseignés, manquants et reconstitués par le modèle.

**Priorité : Must have — Estimation : 5 points**

**Total Must have : 50 points**

---

## Should have — fortement souhaitables (V2)

### US-08 — Historique des scans et favoris
**En tant qu'** utilisateur régulier, **je veux** retrouver l'historique de mes scans et enregistrer des produits en favoris, **afin de** gagner du temps sur mes courses répétées sans avoir à tout rescanner.

*Critères d'acceptation :* l'historique est conservé localement sur l'appareil ; un produit peut être ajouté ou retiré des favoris en un geste.

**Priorité : Should have — Estimation : 3 points**

### US-09 — Profil utilisateur et filtres d'allergènes
**En tant que** Marc, personne diabétique et allergique, **je veux** renseigner un profil avec mes contraintes alimentaires, **afin de** recevoir des alertes lorsqu'un produit contient un allergène ou un ingrédient à surveiller.

*Critères d'acceptation :* les données de profil de santé sont stockées localement sur l'appareil, sans centralisation nominative côté serveur ; la création de profil reste facultative et n'est jamais requise pour utiliser les fonctionnalités du MVP.

**Priorité : Should have — Estimation : 5 points**

**Total Should have : 8 points**

---

## Could have — envisageables (V3)

### US-10 — Personnalisation avancée des recommandations
**En tant qu'** utilisateur ayant défini un objectif nutritionnel pour son foyer, **je veux** que les recommandations et l'ordre d'affichage des produits tiennent compte de cet objectif, **afin de** recevoir des suggestions adaptées à ma situation plutôt que des suggestions génériques.

*Critères d'acceptation :* l'objectif nutritionnel du foyer est un paramètre optionnel ; en son absence, le comportement par défaut de substitution (US-03) reste inchangé.

**Priorité : Could have — Estimation : 8 points**

---

## Won't have — explicitement hors périmètre de cette version

### US-11 — Reconnaissance visuelle d'étiquette (hors backlog estimé)
**En tant qu'** utilisateur pressé, **je veux** photographier une étiquette plutôt que scanner un code-barres, **afin de** analyser un produit même sans emballage lisible par machine.

*Justification de l'exclusion :* traitement par vision par ordinateur non maîtrisé à ce stade du projet ; risque organisationnel et technique jugé disproportionné par rapport à la valeur ajoutée pour le MVP (cf. étude de faisabilité). Cette histoire reste consignée pour traçabilité et sera réévaluée après le jalon J7.

---

## Vue d'ensemble

| Priorité | Nombre d'histoires | Effort total estimé |
|---|---|---|
| Must have | 7 | 50 points |
| Should have | 2 | 8 points |
| Could have | 1 | 8 points |
| Won't have | 1 | non estimé |

Le cœur du MVP (Must have) concentre l'essentiel de l'effort du projet, ce qui confirme la logique du macro-planning : les jalons J3 à J6 sont dédiés à la construction de ces sept histoires, dans l'ordre où elles apparaissent dans la matrice de risques (le modèle de Nutri-Score et le pipeline de données conditionnent tout le reste). Les histoires Should have et Could have ne seront engagées qu'après le jalon J7, une fois le MVP stabilisé et une première base d'utilisateurs constituée.