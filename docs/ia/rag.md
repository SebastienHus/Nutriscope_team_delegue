# Index vectoriel du RAG

Le corpus ([corpus.md](corpus.md)) est découpé en morceaux, vectorisé par Ollama (`qwen3-embedding:0.6b`)
et rangé dans Chroma (service `chroma`). Les outils de l'assistant `chercher_produit`,
`lister_produits` et `chercher_document` y cherchent. Les choix sont dans l'[ADR 0003](../adr/0003-embeddings-et-juge-sur-ollama.md)
(modèle d'embeddings), l'[ADR 0004](../adr/0004-index-vectoriel-chroma.md) (index) et
l'[ADR 0005](../adr/0005-chercher-produit-sur-l-index-rag.md) (outils).

## Commandes

Prérequis : services `ollama` et `chroma` démarrés, fiches et documents générés (voir [corpus.md](corpus.md)).

Le plus simple passe par le pipeline : `make rag` (ou `python -m nutriscope.pipeline sheets`, puis
`embeddings`) écrit les fiches depuis le dernier nettoyé et met l'index à jour, sur le GPU par défaut
(`ARGS="--embed-device cpu"` sur le processeur). Les commandes ci-dessous en sont le détail.

| Commande | Effet |
|---|---|
| `python -m nutriscope.rag.index --device gpu` | indexe les deux collections (~11 min sur le GPU la première fois, ~7 s ensuite si rien n'a changé) |
| `python -m nutriscope.rag.index` | idem sur le processeur (~1 h 20 la première fois) |
| `python -m nutriscope.rag.index --only documents --include-unverified` | une seule collection, avec les sources « à vérifier » |
| `python -m nutriscope.rag.index --limit 200` | essai : au plus 200 morceaux vectorisés, la suite au prochain lancement |
| `python -m nutriscope.rag.index --rebuild` | supprime et reconstruit (obligatoire après un changement de modèle) |
| `python -m nutriscope.rag.search "pâte à tartiner moins sucrée" -k 5` | les morceaux les plus proches dans chaque collection |
| `python -m nutriscope.rag.search "peu salé" --section Cheese` | idem, fiches limitées à un rayon (valeur exacte de `section`, en anglais : `Cheese`, `Sweets`…) ; les documents ne sont pas filtrés |
| `python -m nutriscope.rag.search "pâte à tartiner" --no-instruction` | question vectorisée sans consigne, pour mesurer ce que la consigne apporte |

Depuis Python :

```python
from nutriscope.rag.search import search, search_all
hits = search("fromage peu salé", collection="sheets", k=5, where={"incomplete_data": False})
for hit in hits:
    print(hit.score, hit.id, hit.citation)
```

## Collections

| Collection | Morceaux | Identifiant | Métadonnées |
|---|---|---|---|
| `sheets` | une fiche par produit du nettoyé du pipeline (5 316, les produits de la base) | `fiche:<code>` | `family`, `code`, `name`, `brand`, `section`, `nutriscore` (lettre), `incomplete_data`, `source` ; pour la fiche de `chercher_produit` : `brands`, `quantity`, `pnns_group_1`, `pnns_group_2`, `labels`, `nutriscore_score`, `nova_group` et les valeurs `*_100g` ; `text_hash`, `meta_hash` |
| `documents` | morceaux des documents de référence (16 pour la seule source autorisée ; 281 avec `--include-unverified`) | `doc:<id>:<n>` | `family`, `source_id`, `chunk`, `page` (PDF), `title`, `publisher`, `url`, `updated`, `license`, `status`, `sha256`, `text_hash`, `meta_hash` |

Le texte stocké est le texte d'origine : c'est lui qui est renvoyé et cité. Le texte vectorisé peut
différer légèrement (ci-dessous) ; son empreinte `text_hash` sert à ne revectoriser que ce qui change.
`meta_hash` couvre le texte stocké et les métadonnées : s'ils changent seuls, le vecteur déjà
enregistré est gardé (Chroma refuse de mettre à jour un document sans vecteur, l'index relit donc le
vecteur stocké et le renvoie).

## Découpage

- **Fiche produit** : un morceau par fiche. Le texte vectorisé omet la ligne « Source : », identique
  sur toutes les fiches : elle rapprocherait toutes les fiches entre elles sans aider à les distinguer.
- **Document** : morceaux d'au plus 800 caractères (médiane 690), faits de phrases entières ; chaque
  morceau reprend les dernières phrases du précédent, dans la limite de 150 caractères. Un morceau ne
  franchit jamais un marqueur `[page N]`, la page citée est donc exacte. Les morceaux de moins de
  40 caractères (page de garde, page vide) sont écartés.
- **PDF** : pypdf coupe les lignes en pleine phrase ; dans une page, les retours à la ligne deviennent
  des espaces. Rien d'autre n'est modifié (décision Vie publique, « ne pas modifier le contenu »).
- Le texte vectorisé d'un morceau de document est précédé du titre du document, pour situer le passage.

## Vectorisation

- **Documents** : texte brut, sans consigne.
- **Questions** : précédées de la consigne recommandée par la fiche du modèle, en anglais :
  `Instruct: Given a question about food products or nutrition, retrieve the passage that answers it\nQuery:<question>`.
- **Matériel** : les questions sont toujours vectorisées sur le processeur (alias `qwen3-embedding-cpu:0.6b`,
  `num_gpu 0`, `OLLAMA_EMBED_THREADS` threads). L'indexation en masse peut passer par le GPU
  (`--device gpu`, modèle de base) : mêmes poids, mêmes vecteurs (cosinus ≥ 0,9995).
- **Contexte** : 2 048 tokens par appel (un morceau en fait au plus ~300) ; la valeur est fixe, sinon
  Ollama recharge le modèle.

## Outils de l'assistant

| Outil | Arguments | Recherche | Résultat |
|---|---|---|---|
| `chercher_produit` (contrat du TP 18) | `nom` ou `code`, `limite` 1 à 5 | code : lecture directe de `fiche:<code>` ; nom : 20 fiches les plus proches, puis celles dont le nom ou une marque contient tous les mots, sinon repli sémantique (≥ 0,5 et à moins de 0,03 de la meilleure) | `ok` / `ambigu` / `introuvable`, fiches chiffrées rendues depuis les métadonnées |
| `lister_produits` (questions de liste) | `mots` (1 à 5 mots-clés, sans article ni préposition), `nutriscore_max` A à E, `tri` (`nutriscore`, `kcal`, `sucres`, `sel`, `satures`, `lipides`, `fibres`, `proteines`), `limite` 1 à 5 (5 par défaut) | toutes les fiches dont le nom, la marque ou la catégorie (libellé français du groupe PNNS) contient chaque mot-clé en mot entier, singulier ou pluriel ; sinon repli sémantique (≥ 0,5, à moins de 0,05 de la meilleure) ; puis filtre Nutri-Score sur les produits trouvés (aucun jus d'orange noté B : `introuvable`, pas des jus de citron) ; tri sur la valeur, non renseignée en dernier | `ok` / `introuvable` (jamais `ambigu`), fiches réduites précédées de leur `rang` |
| `chercher_document` | `question`, `limite` 1 à 5 | passages de la collection `documents` à au moins 0,5 | `ok` / `introuvable`, texte d'origine avec éditeur, titre, page, date |

Le moteur est `nutriscope.rag.retriever.RagIndex`, le catalogue de l'assistant et du scanner (la
recherche SQL du TP 18 a été retirée). Garde-fous ajoutés dans l'agent :

- produit `ambigu` qu'aucune recherche `ok` n'a tranché → question de précision construite en code
  (3 candidats au plus, avec marque et code-barres), le modèle ne choisit jamais ; une liste
  `lister_produits` réussie lève la question (l'utilisateur voulait plusieurs produits) ;
- réponse coupée par la limite de tokens → réponse de repli, jamais un texte tronqué ;
- chiffres sans aucun outil appelé → l'agent lance lui-même l'outil de la collection la plus proche
  de la question (`RagIndex.closest_collection` : documents si un passage dépasse toute fiche et
  0,5, sinon fiches ; mesuré sur 14 questions, écart de +0,15 à +0,27 pour les questions générales,
  de -0,02 à -0,27 pour les questions produit) ;
- question générale sans passage trouvé → réponse fixe ;
- réponse de repli → le passage le plus proche, cité mot pour mot.

### Listes (`lister_produits`, 19/11/2026)

Pourquoi les mots d'abord : avec un filtre Nutri-Score, la similarité des bons produits s'effondre
(biscuits notés A ou B : 0,48 au mieux, sous le seuil) ; et elle ne départage pas un biscuit de la
catégorie (0,27 à 0,46) d'un poisson « pané aux céréales » (0,44). En mot entier, « chips » ne trouve
plus « Archipel » ni « Chipolata ». Les catégories PNNS sont en anglais : sans libellé français,
« céréales du petit-déjeuner » trouvait 1 des 87 « Breakfast cereals », 87 avec.

Des mots-clés plutôt qu'une phrase : la recherche exige chaque mot, donc « du » ou « au » devaient
être écartés. La fréquence ne les distingue pas dans ce catalogue (noms courts, souvent étrangers) :
« du » est dans 2,5 % des fiches, moins que « biscuits » (8,7 %) ; pondérer par l'IDF faisait tomber
« céréales du petit-déjeuner » de 87 fiches à 1. Plutôt qu'une liste de mots vides, c'est le modèle qui
donne les mots-clés (`mots`) : sur 10 questions de liste, aucun article ni préposition, mêmes produits
qu'avec la liste. Il fallait dire « le type et toutes ses précisions (nature, parfum, origine) » :
sinon il retirait « nature » des yaourts. BM25 (bm25s + racinisation Snowball) a aussi été essayé : à
couverture complète, il ne fait que raciniser (gain marginal, 2,5 s de construction) ; à 60 % ou
fusionné avec l'embedding, il ajoute du bruit que le tri fait remonter (une whey en tête des
« yaourts nature »).

| Recherche | Produits retenus |
|---|---|
| « biscuits » | 462 (461 « Biscuits and cakes ») |
| « céréales du petit-déjeuner » | 87 (toutes « Breakfast cereals ») |
| « yaourt nature » | 10 |
| « chips » | 141 (124 « Appetizers ») |
| « fruits » | 302 (fruits, jus, fruits secs ; plus les légumes ni le poisson) |
| « ordinateur portable » | `introuvable` |

Avec le modèle (qwen3-vl-4b, llama.cpp) : 6 questions de liste sur 6 passent par `lister_produits`
avec des arguments justes (« bien notés » → `nutriscore_max` B, « moins sucrées » → `tri` sucres) ;
les questions produit, de comparaison et générales ne changent pas d'outil. Sans `rang`, le modèle
inversait parfois l'ordre (jus d'orange) ; avec cinq fiches complètes, le contexte de 4 096 tokens
débordait, d'où les fiches réduites.

### Calibrage (18/11/2026)

| Mesure | Résultat |
|---|---|
| 100 noms tirés au hasard dans l'index | 100 retrouvés dans les 5 premiers : 75 `ok`, 25 `ambigu` |
| Produits absents : « ordinateur portable », « Big Mac », « pneu de vélo », « Evian » | `introuvable` (meilleur score 0,41 à 0,50) |
| « prince lu », « Kinder Bueno », « coca zero » | trouvés par les mots (scores 0,45 à 0,72) |
| « nutela » | Nutella B-Ready, par le repli sémantique |
| 200 codes : fiche RAG contre fiche SQL | mêmes statuts et nutriments ; marque `null` pour 169 produits côté SQL, renseignée côté RAG |
| Documents, questions du sujet | 0,61 à 0,81 (« couleurs du logo » : 0,47, sous le seuil) |
| Documents, questions hors sujet | 0,28 à 0,48 |

## Premiers essais (18/11/2026)

| Question | Collection pertinente | Constat |
|---|---|---|
| « pâte à tartiner moins sucrée » | `sheets` | trois pâtes à tartiner (0,59 à 0,67), mais **pas classées par teneur en sucre** : la similarité ne sait pas comparer des valeurs |
| « fromage peu salé » | `sheets` | trois fromages (~0,54), même limite pour le sel |
| « comment est calculé le Nutri-Score ? » | `documents` | passages Vie publique à ~0,80 ; les fiches remontent quand même (~0,60) sans rapport avec la question |
| « Le Nutri-Score est-il obligatoire ? » | `documents` | passages Vie publique à ~0,80 |

À retenir pour l'outil de l'assistant :

- les scores des fiches sont serrés (0,54 à 0,67) : toutes les fiches partagent la même structure ;
  un seuil fixe ne suffit pas à dire « aucune fiche pertinente » ;
- un écart net entre les deux collections (~0,8 contre ~0,6) indique une question générale plutôt
  qu'une question produit ;
- « moins sucré », « peu salé » demandent un filtre ou un tri sur les valeurs : à combiner avec la
  recherche (métadonnées ou base SQL), pas à attendre de la similarité seule. C'est ce que fait
  `lister_produits` (19/11/2026).

## Limites connues

- **Restes de mise en page** : le début de la page Vie publique garde quelques lignes de navigation
  (« Enquête », « Temps de lecture ») ; l'en-tête courant du PDF PNNS (« Santé publique France /
  Recommandations… / p. N ») revient en tête de chaque page. À nettoyer dans `scraping.py` si ces
  lignes gênent la recherche.
- **Sources « à vérifier »** : tant que l'équipe n'a pas lu leurs mentions légales, elles restent
  hors de l'index par défaut ; seule la page Vie publique y entre.
- **`total` plafonné à 20** pour une recherche par nom (le SQL comptait toutes les correspondances) ;
  une recherche vague (« de ») rend `ambigu`, pas une erreur.
- **Listes** : un mot du nom peut être un ingrédient (« cabillaud pané aux céréales » dans les
  céréales, « Chips de banane » dans les chips) ; le classement porte sur l'échantillon (5 316
  produits), pas sur le marché ; un critère hors des valeurs (« sans sucre ») passe par le repli
  sémantique, bruité (« boisson sans sucre » : une compote, un sucre vanillé).
- **Contexte du modèle** (4 096 tokens) : prompt et trois outils en prennent ~2 800 ; une recherche
  d'alternative (fiche du produit + liste) laisse ~240 tokens pour répondre, et une relecture de plus
  ne tient pas (réponse de repli). `LLM_CTX` plus grand si la mémoire graphique le permet.
- **Données d'Open Food Facts** reprises telles quelles, erreurs comprises (ex. « Coca Cola Zero »
  à 335 kcal, code 5993330000190).
- **Seuils** (0,5 pour les noms et les documents, marge 0,03) mesurés sur l'échantillon : à remesurer
  si le corpus ou le modèle d'embeddings change.
