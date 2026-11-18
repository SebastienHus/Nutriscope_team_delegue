# Index vectoriel du RAG

Le corpus ([corpus.md](corpus.md)) est découpé en morceaux, vectorisé par Ollama (`qwen3-embedding:0.6b`)
et rangé dans Chroma (service `chroma`). Les choix sont dans l'[ADR 0003](../adr/0003-embeddings-et-juge-sur-ollama.md)
(modèle d'embeddings) et l'[ADR 0004](../adr/0004-index-vectoriel-chroma.md) (index).

## Commandes

Prérequis : services `ollama` et `chroma` démarrés, fiches et documents générés (voir [corpus.md](corpus.md)).

| Commande | Effet |
|---|---|
| `python -m nutriscope.rag.index --device gpu` | indexe les deux collections (~11 min sur le GPU la première fois, ~7 s ensuite si rien n'a changé) |
| `python -m nutriscope.rag.index` | idem sur le processeur (~1 h 20 la première fois) |
| `python -m nutriscope.rag.index --only documents --include-unverified` | une seule collection, avec les sources « à vérifier » |
| `python -m nutriscope.rag.index --limit 200` | essai : au plus 200 morceaux vectorisés, la suite au prochain lancement |
| `python -m nutriscope.rag.index --rebuild` | supprime et reconstruit (obligatoire après un changement de modèle) |
| `python -m nutriscope.rag.search "pâte à tartiner moins sucrée" -k 5` | les morceaux les plus proches dans chaque collection |

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
| `sheets` | une fiche par produit (5 963) | `fiche:<code>` | `family`, `code`, `name`, `brand`, `section`, `nutriscore`, `incomplete_data`, `source`, `text_hash` |
| `documents` | morceaux des documents de référence (16 pour la seule source autorisée ; 281 avec `--include-unverified`) | `doc:<id>:<n>` | `family`, `source_id`, `chunk`, `page` (PDF), `title`, `publisher`, `url`, `updated`, `license`, `status`, `sha256`, `text_hash` |

Le texte stocké est le texte d'origine : c'est lui qui est renvoyé et cité. Le texte vectorisé peut
différer légèrement (ci-dessous) ; son empreinte `text_hash` sert à ne revectoriser que ce qui change.

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
  recherche (métadonnées ou base SQL), pas à attendre de la similarité seule.

## Limites connues

- **Restes de mise en page** : le début de la page Vie publique garde quelques lignes de navigation
  (« Enquête », « Temps de lecture ») ; l'en-tête courant du PDF PNNS (« Santé publique France /
  Recommandations… / p. N ») revient en tête de chaque page. À nettoyer dans `scraping.py` si ces
  lignes gênent la recherche.
- **Sources « à vérifier »** : tant que l'équipe n'a pas lu leurs mentions légales, elles restent
  hors de l'index par défaut ; seule la page Vie publique y entre.
- **L'outil de l'assistant** n'est pas encore branché : il remplacera la recherche SQL
  (`chercher_produit`) dans une étape suivante.
