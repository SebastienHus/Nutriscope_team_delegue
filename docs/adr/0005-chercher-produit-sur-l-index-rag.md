# ADR 0005 — `chercher_produit` cherche dans l'index du RAG, avec le même contrat ; `chercher_document` s'y ajoute

Date : 18/11/2026 — Statut : **acceptée** — Suit l'ADR 0004 (index Chroma)

## Contexte

L'équipe remplace la recherche SQL de l'assistant par le RAG. Mais `chercher_produit` est « le seul
contrat imposé » du brief (TP 18) : arguments `nom` / `code` / `limite`, statut `ok` / `ambigu` /
`introuvable`, fiche avec des nutriments **chiffrés**. Il resservira tel quel aux TP 21 et 23, et le
scanner d'étiquettes l'appelle pour vérifier une lecture.

Deux difficultés :

- une recherche sémantique rend **toujours** des voisins : sans règle, aucun produit ne serait jamais
  « introuvable » ;
- les fiches du RAG venaient d'un autre nettoyé (5 963 produits) que la base (5 316).

## Décision

- **Le contrat ne change pas, le moteur si.** `RagIndex` (`rag/retriever.py`) offre la même interface
  que le catalogue SQL (`find_by_code`, `search_by_name`) et rend des lignes au format de la base ;
  `build_fiche` en fait la fiche du contrat. `chercher_produit` et le scanner ne voient pas la
  différence. **La recherche SQL (`PostgresCatalog`) est retirée** : elle ne servait plus qu'à
  l'assistant. La base PostgreSQL reste chargée par le pipeline (`load_database`), pour les analyses.
- **Les fiches portent leurs valeurs.** `metadata.jsonl` (et donc l'index) contient marques, quantité,
  groupes PNNS, labels, score Nutri-Score, NOVA et valeurs pour 100 g : plus besoin de la base pour
  rendre une fiche.
- **Une seule source : le nettoyé du pipeline.** L'étape `sheets` écrit les fiches depuis
  `products_clean_<date>.parquet`, l'étape `embeddings` met l'index à jour : fiches, index et base
  portent les mêmes 5 316 produits.
- **Code-barres** : lecture directe de `fiche:<code>` (variantes UPC-A / EAN-13 comprises).
- **Nom** : les 20 fiches les plus proches ; parmi elles, celles dont le nom ou une marque contient
  **tous** les mots (règle du SQL), quel que soit le score ; sinon repli sémantique (score ≥ 0,5 et à
  moins de 0,03 de la meilleure) ; sinon `introuvable`. `total` compte les fiches retenues, au plus 20.
- **Nouvel outil `chercher_document`** (contrat de l'équipe : `question`, `limite`) : passages
  d'origine des documents de référence, avec éditeur, titre, page et date ; `introuvable` sous 0,5.
- **Nouvel outil `lister_produits`** (19/11/2026) pour les questions de liste (« quels biscuits sont
  bien notés ? ») : elles passaient par `chercher_produit`, dont le statut `ambigu` déclenchait une
  question de précision. `chercher_produit` désigne un produit, `lister_produits` filtre (Nutri-Score)
  et classe (une valeur pour 100 g) les produits d'un type ; jamais `ambigu`, 5 fiches réduites au plus.
  Le modèle donne des mots-clés (`mots`), sans article ni préposition : pas de liste de mots vides.
- **Garde-fous en code**, parce que le modèle 4B ne suit pas toujours le prompt :
  - produit `ambigu` qu'aucune recherche `ok` n'a tranché : l'agent répond par une question de
    précision construite en code (candidats, marque, code-barres). Le modèle choisissait sinon un
    produit à la place de l'utilisateur (comparaison des Coca light et zéro, mesuré). Une liste
    `lister_produits` réussie lève la question ;
  - question générale sans passage trouvé : réponse fixe, le modèle n'ajoute rien de mémoire (il
    citait des organismes inventés) ;
  - réponse avec des chiffres sans aucun outil appelé : le code lance lui-même l'outil de la
    collection la plus proche de la question (`chercher_document` si un passage dépasse toute fiche,
    sinon `chercher_produit`) et donne le résultat au modèle pour sa relecture (llama.cpp ignore
    `tool_choice="required"` avec ce modèle, mesuré) ;
  - réponse de repli : le passage le plus proche, cité mot pour mot avec sa source ;
  - réponse coupée par la limite de tokens : réponse de repli, jamais un texte tronqué.

## Ce qu'on a mesuré (18/11/2026)

| Mesure | Résultat |
|---|---|
| 100 noms de produits tirés au hasard | 100 retrouvés dans les 5 premiers : 75 `ok`, 25 `ambigu` (homonymes) |
| Produits absents (« ordinateur portable », « Big Mac », « Evian ») | `introuvable` |
| « prince lu » (nom court, score 0,45) | les 2 Prince de LU, grâce aux mots |
| « nutela » (faute de frappe) | Nutella B-Ready, par le repli sémantique |
| 200 codes : fiche RAG contre fiche SQL | mêmes statuts et mêmes nutriments (à un arrondi près : 7,957 contre 7,956 g) |
| Documents : questions du sujet / hors sujet | 0,61 à 0,81 / 0,48 au plus (seuil 0,5) |

La comparaison avec le SQL a aussi montré que **la base a perdu des marques** : `marque` est `null`
pour 169 des 200 produits côté SQL, renseignée côté RAG (à corriger dans `load_database`).

## Conséquences

- ➕ Contrat du brief, scanner et tests du TP 18 inchangés ; l'assistant gagne les questions générales.
- ➕ Recherche tolérante aux fautes et aux reformulations (« Coca-Cola Zero » trouve « Coca cola zéro »).
- ➖ L'assistant dépend maintenant de Chroma **et** d'Ollama (vectorisation de la question, ~0,1 s sur le
  processeur) ; sans eux, l'outil renvoie `{"erreur": "tool unavailable"}`.
- ➖ `total` est plafonné à 20 (le SQL comptait toutes les correspondances) ; une recherche vague
  (« de ») rend `ambigu` au lieu d'une erreur.
- ➖ Seuils (0,5) et marge (0,03) mesurés sur l'échantillon : à remesurer si le corpus ou le modèle change.
- ➖ Les erreurs d'Open Food Facts passent telles quelles (ex. un « Coca Cola Zero » à 335 kcal,
  code 5993330000190), comme avec le SQL.

Sources : brief TP 18 (contrat de `chercher_produit`) ; mesures du 18/11/2026 (docs/ia/rag.md).
