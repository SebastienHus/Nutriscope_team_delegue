# Backlog Produit — Projet IA NutriScope
### TP 8 · Jalon J2 · Version v0.2

**Équipe :** Sébastien HUS / Nicolas CUSUMANO  
**Date :** 17/09/2026

---

## Méthode de Priorisation et d'Estimation

Le backlog reprend l'ensemble des besoins déjà spécifiés dans le cahier des charges, formulés en histoires utilisateur (user stories) au format « En tant que…, je veux…, afin de… », complétées de leurs critères d'acceptation. Chaque histoire est priorisée selon la méthode **MoSCoW** :

- **Must have** : indispensable au MVP
- **Should have** : fortement souhaitable mais différable  
- **Could have** : envisageable si le temps le permet
- **Won't have** : explicitement écarté pour cette version

Chaque histoire est estimée en points d'effort (échelle : 2, 3, 5, 8, 13 points) — une mesure relative qui reflète la taille et l'incertitude, non une durée en heures. L'estimation reste approximative à ce stade et sert à comparer les histoires entre elles et à vérifier la cohérence de la charge du MVP avec les 216 heures allouées au projet fil rouge.

---

## Must Have — Indispensables au MVP

### US-01 — Scan et Recherche de Produit

**En tant que** Sophie, parent pressé faisant ses courses  
**Je veux** scanner le code-barres d'un produit en magasin ou saisir son nom dans la barre de recherche  
**Afin de** accéder instantanément à sa fiche d'analyse nutritionnelle sans perdre de temps en rayon

*Critères d'acceptation :*
- Le temps de réponse pour retourner la fiche produit est inférieur à 500 ms
- Si le code-barres est absent du catalogue, un message clair informe l'utilisateur sans provoquer d'erreur bloquante

**Priorité : Must have — Estimation : 5 points**

---

### US-02 — Transparence et Nutri-Score Prédit

**En tant qu'** utilisateur soucieux de sa santé  
**Je veux** voir la fiche nutritionnelle simplifiée et connaître le Nutri-Score réel ou prédit par le modèle  
**Afin de** comprendre rapidement la qualité du produit même si l'étiquette d'origine est incomplète

*Critères d'acceptation :*
- Si le Nutri-Score d'origine est manquant, la valeur prédite est affichée avec une mention explicite
- Un indice de confiance est systématiquement affiché
- L'explication des points forts et faibles est rédigée dans un langage pédagogique et non culpabilisant

**Priorité : Must have — Estimation : 8 points**

---

### US-03 — Recommandation d'Alternatives (Substitution)

**En tant que** consommateur cherchant de meilleurs choix  
**Je veux** obtenir une à trois propositions d'alternatives plus saines équivalentes dans le même rayon  
**Afin de** remplacer facilement un produit mal noté par un autre mieux équilibré

*Critères d'acceptation :*
- Les alternatives suggérées appartiennent strictement à la même catégorie ou sous-catégorie
- Les produits recommandés présentent un Nutri-Score strictement meilleur que le produit scanné

**Priorité : Must have — Estimation : 8 points**

---

### US-04 — Assistant Nutritionnel Conversationnel (RAG)

**En tant qu'** utilisateur se posant des questions sur la composition d'un produit  
**Je veux** poser une question en langage naturel sur le produit scanné  
**Afin d'** obtenir une réponse synthétique, vérifiée et facile à comprendre

*Critères d'acceptation :*
- L'assistant s'appuie uniquement sur des données factuelles vérifiées, sans invention
- Chaque réponse cite sa source
- Le corpus interrogé réunit les fiches du catalogue et des sources publiques de référence en nutrition
- Les réponses intègrent un rappel de l'absence de conseil médical direct
- L'assistant refuse explicitement les questions hors du périmètre alimentaire et nutritionnel (conseil médical déguisé, sujet sans rapport)

**Priorité : Must have — Estimation : 13 points**

---

### US-05 — Pipeline Automatisé d'Ingestion et Nettoyage

**En tant que** responsable des données  
**Je veux** exécuter un pipeline de nettoyage rejouable sur le catalogue Open Food Facts  
**Afin de** filtrer les doublons, éliminer les valeurs aberrantes et structurer la base d'analyse

*Critères d'acceptation :*
- Le script d'ingestion s'exécute de manière automatisée
- Les données corrompues ou invalides sont isolées et journalisées dans un rapport d'audit

**Priorité : Must have — Estimation : 8 points**

---

### US-06 — Gestion des Produits Inconnus et des Incertitudes

**En tant qu'** utilisateur scannant un produit non répertorié ou très incomplet  
**Je veux** être informé clairement si le produit est inconnu ou si la fiabilité de la prédiction est trop faible  
**Afin de** ne pas recevoir d'information erronée ou de prédiction trompeuse

*Critères d'acceptation :*
- Si la confiance du modèle est inférieure à 50 %, l'application affiche « données insuffisantes pour estimer le score »
- L'utilisateur peut signaler un produit manquant ou une incohérence

**Priorité : Must have — Estimation : 3 points**

---

### US-07 — Détail Explicatif de l'Indice de Confiance

**En tant qu'** utilisateur souhaitant vérifier l'origine d'un résultat  
**Je veux** consulter le détail du calcul en cliquant sur l'indice de confiance  
**Afin de** comprendre quelles données ont servi au calcul (réelles vs estimées)

*Critères d'acceptation :*
- Un volet explicatif liste clairement les nutriments renseignés, manquants et reconstitués par le modèle

**Priorité : Must have — Estimation : 5 points**

---

### US-12 — Classification Automatique de la Catégorie (Computer Vision)

**En tant qu'** équipe data / IA  
**Je veux** un modèle qui reconnaît automatiquement la catégorie d'un produit à partir de sa photo  
**Afin de** compléter la catégorie d'un produit lorsque cette donnée est absente ou peu fiable dans le catalogue

*Critères d'acceptation :*
- Le modèle est évalué sur un jeu de photos représentatif des rayons du périmètre
- L'exactitude par catégorie est documentée
- Les catégories mal reconnues sont identifiées et signalées
- Cette classification reste un signal interne, jamais présentée à l'utilisateur final comme une fonctionnalité de scan photo

**Priorité : Must have — Estimation : 8 points**

---

### US-13 — Attribution des Sources de Données

**En tant qu'** équipe projet  
**Je veux** afficher un crédit visible à Open Food Facts dans l'application et chaque document livré  
**Afin de** respecter les obligations de la licence ODbL (base de données) et CC-BY-SA (photographies)

*Critères d'acceptation :*
- Un crédit Open Food Facts est visible dans l'application (pied de fiche produit)
- Chaque document livré porte la même mention
- La conformité de la valorisation B2B avec la clause de partage à l'identique est vérifiée avant J7

**Priorité : Must have — Estimation : 2 points**

---

### US-14 — Segmentation du Catalogue en Familles Comparables

**En tant qu'** équipe data / IA  
**Je veux** regrouper automatiquement les produits en familles nutritionnellement comparables  
**Afin de** donner au moteur de substitution un périmètre de recherche pertinent

*Critères d'acceptation :*
- Le nombre de groupes retenu est justifié et documenté
- Chaque groupe reçoit une interprétation et un nom compréhensibles par un non-technicien
- Les groupes sont confrontés aux rayons réels du périmètre
- Les regroupements incohérents sont documentés

**Priorité : Must have — Estimation : 5 points**

---

### US-15 — Tableau de Bord de la Qualité du Catalogue

**En tant que** membre de la direction  
**Je veux** consulter un tableau de bord qui montre l'état et la qualité du catalogue produits  
**Afin de** comprendre sur quelles données repose l'application sans avoir à lire un carnet technique

*Critères d'acceptation :*
- Le tableau se lit sans compétence technique (chaque graphique porte un titre qui affirme un message)
- Il couvre : complétude par rayon et marque, répartition des Nutri-Score, volume de produits retenus
- Il est régénéré automatiquement à chaque exécution du pipeline

**Priorité : Must have — Estimation : 5 points**

---

### US-16 — Supervision de l'Application en Production

**En tant que** responsable d'exploitation  
**Je veux** disposer d'un suivi permanent du fonctionnement de l'application  
**Afin de** détecter une panne ou une dérive par la surveillance plutôt que par une réclamation utilisateur

*Critères d'acceptation :*
- L'application expose un point de contrôle de santé surveillé avec alertes en cas de panne
- Les journaux tracent pour chaque appel : chemin emprunté, temps de réponse, statut
- Pour chaque conversation : outil sollicité, coût estimé
- Un tableau de bord d'exploitation présente : trafic, temps de réponse, taux d'erreur, coût cumulé
- Le jeu d'évaluation de l'assistant et un échantillon de prédictions sont rejoués automatiquement
- Les résultats sont archivés pour détecter une dérive

**Priorité : Must have — Estimation : 3 points**

**Total Must have : 73 points**

---

## Should Have — Fortement Souhaitables (V2)

### US-08 — Historique des Scans et Favoris

**En tant qu'** utilisateur régulier  
**Je veux** retrouver l'historique de mes scans et enregistrer des produits en favoris  
**Afin de** gagner du temps sur mes courses répétées sans tout rescanner

*Critères d'acceptation :*
- L'historique est conservé localement sur l'appareil
- Un produit peut être ajouté ou retiré des favoris en un geste

**Priorité : Should have — Estimation : 3 points**

---

### US-09 — Profil Utilisateur et Filtres d'Allergènes

**En tant que** Marc, personne diabétique et allergique  
**Je veux** renseigner un profil avec mes contraintes alimentaires  
**Afin de** recevoir des alertes lorsqu'un produit contient un allergène ou un ingrédient à surveiller

*Critères d'acceptation :*
- Les données de profil de santé sont stockées localement sur l'appareil, sans centralisation nominative côté serveur
- La création de profil reste facultative et n'est jamais requise pour utiliser les fonctionnalités du MVP

**Priorité : Should have — Estimation : 5 points**

**Total Should have : 8 points**

---

## Could Have — Envisageables (V3)

### US-10 — Personnalisation Avancée des Recommandations

**En tant qu'** utilisateur ayant défini un objectif nutritionnel pour son foyer  
**Je veux** que les recommandations et l'ordre d'affichage tiennent compte de cet objectif  
**Afin de** recevoir des suggestions adaptées à ma situation plutôt que des suggestions génériques

*Critères d'acceptation :*
- L'objectif nutritionnel du foyer est un paramètre optionnel
- En son absence, le comportement par défaut de substitution (US-03) reste inchangé

**Priorité : Could have — Estimation : 8 points**

---

## Won't Have — Explicitement Hors Périmètre

### US-11 — Reconnaissance Visuelle d'Étiquette (OCR Photo)

**En tant qu'** utilisateur pressé  
**Je veux** photographier une étiquette plutôt que scanner un code-barres  
**Afin de** analyser un produit même sans emballage lisible par machine

**Justification de l'exclusion :**  
Traitement par vision par ordinateur non maîtrisé à ce stade du projet. Risque organisationnel et technique jugé disproportionné par rapport à la valeur ajoutée pour le MVP. Cette histoire reste consignée pour traçabilité et sera réévaluée après le jalon J7.

---

## Vue d'Ensemble

| Priorité | Nombre d'histoires | Effort total estimé |
|---|---|---|
| **Must have** | 12 | 73 points |
| **Should have** | 2 | 8 points |
| **Could have** | 1 | 8 points |
| **Won't have** | 1 | non estimé |
| **TOTAL** | **16** | **89 points** |

---

## Notes de Cadrage

### Coherence Charge vs Budget
Ce total de 73 points pour le MVP doit être confronté à l'enveloppe de 216 heures du projet. Si un point d'effort représente environ **2 à 3 heures** de travail d'équipe, le MVP situe autour de **150 à 200 heures**, laissant peu de marge pour imprévus.

**Conséquence** : Aucune histoire Should have ou Could have ne sera engagée avant le jalon J7. Tout ajout de périmètre en cours de route devra s'accompagner du retrait d'autre chose.

### Ordre de Priorité dans le Planning
Le macro-planning des jalons J3 à J6 est directement dérivé de l'ordre des histoires Must have :

1. **J3** — Modèle Nutri-Score + indice de confiance (US-02, US-07)
2. **J4** — Moteur de substitution (US-03)
3. **J5** — Assistant RAG (US-04)
4. **J6** — Intégration complète, supervision, déploiement

Les histoires **Should have** et **Could have** ne seront engagées qu'après le jalon J7, une fois le MVP stabilisé et une première base d'utilisateurs constituée.

### Prérequis Techniques
- **US-05** (Pipeline nettoyage) est **critique** — elle conditionne toutes les autres analyses et prédictions
- **US-14** (Segmentation en familles) doit être complétée avant **US-03** (Substitution)
- **US-12** (Classification image) est optionnelle pour le MVP mais améliore la complétude du catalogue