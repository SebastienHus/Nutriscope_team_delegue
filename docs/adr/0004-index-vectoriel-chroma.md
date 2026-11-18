# ADR 0004 — L'index vectoriel est un serveur Chroma à deux collections, rempli avec nos propres vecteurs

Date : 18/11/2026 — Statut : **acceptée** — Complète l'ADR 0003 (embeddings servis par Ollama)

## Contexte

Le RAG (module 6.3) doit retrouver, pour une question, les fiches produits et les passages des documents
de référence les plus proches. Le corpus compte **5 963 fiches** (une par produit du catalogue nettoyé)
et **4 documents** (281 morceaux, dont 16 pour la seule source autorisée aujourd'hui), voir
[docs/ia/corpus.md](../ia/corpus.md). La recherche avec NumPy seul (séquence 2 du 17/11) suffit
pour 50 fiches, mais pas pour un index persistant partagé par l'assistant et les scripts.

Plus tard, l'outil de recherche de l'assistant passera par cet index et **remplacera la recherche
SQL** (`chercher_produit`).

## Options

1. **Chroma embarqué** (`chromadb.PersistentClient`, fichiers dans `data/`) : rien à déployer, mais
   l'index n'est accessible qu'au processus Python qui l'ouvre, et le paquet `chromadb` complet
   (ONNX, modèle d'embeddings par défaut) est lourd et fragile sous Python 3.14.
2. **Chroma en serveur** (service `chroma` de `compose.yml`) : un index partagé par l'API, l'assistant
   et les scripts ; côté Python, seulement le client HTTP `chromadb-client`.
3. **pgvector dans PostgreSQL** : une seule base, mais une extension à ajouter à l'image `db`, et le
   module 6.3 est construit autour de Chroma.

Pour le rangement : une seule collection avec un champ `family`, ou **deux collections**.

## Décision

- **Option 2, Chroma 1.5.9 en serveur**, durci comme les autres services (`read_only`, `cap_drop ALL`,
  réseau interne `inference`, volume `chroma_data`), publié en dev sur `127.0.0.1:8001`.
- **Deux collections**, `sheets` et `documents`, interrogées chacune avec son propre `k` : dans une
  collection unique, les 5 963 fiches noieraient les quelques dizaines de passages de documents
  parmi les plus proches voisins.
- **Nos propres vecteurs** : Chroma ne calcule rien (`embedding_function=None`). Les vecteurs viennent
  de `qwen3-embedding:0.6b` (Ollama), et le nom du modèle est enregistré dans les métadonnées de la
  collection : un index construit avec un autre modèle est refusé (`--rebuild` pour le reconstruire).
- **Distance cosinus.** Les vecteurs d'Ollama sont normalisés ; le score renvoyé est la similarité
  cosinus.
- **Indexation incrémentale** : chaque morceau porte l'empreinte du texte vectorisé (`text_hash`) ;
  seuls les morceaux nouveaux ou modifiés sont revectorisés, ceux qui ont disparu sont supprimés.
- **Indexation en masse sur le GPU** (`--device gpu`), **questions sur le processeur**. C'est un
  ajustement de l'ADR 0003 : les mêmes poids donnent les mêmes vecteurs sur les deux matériels
  (cosinus ≥ 0,9995 mesuré sur 32 fiches), donc l'index ne retient que l'identité du modèle
  (`OLLAMA_EMBED_MODEL`), pas le matériel.

## Ce qu'on a mesuré

Mesures du 18/11/2026, même poste que l'ADR 0003 (16 processeurs logiques, Quadro RTX 4000 8 Go).

| Configuration | Débit | Fiches complètes (5 963) |
|---|---|---|
| Processeur, 8 threads sur un quota de 4 processeurs (alias d'origine) | ~1,1 s par fiche | ~1 h 50 |
| Processeur, 4 threads (`OLLAMA_EMBED_THREADS`, nouvel alias) | ~0,8 s par fiche | ~1 h 20 |
| GPU, modèle de base, llama.cpp en marche | ~0,11 s par fiche | 11 min 20 s (mesuré) |

Sur le GPU, le modèle d'embeddings prend ~2,1 Go : avec llama.cpp, la carte monte à 7,45 Go sur 8.
Ça tient, mais de justesse ; en cas d'erreur de mémoire, arrêter llama.cpp le temps de l'indexation.

## Conséquences

- ➕ Un seul index, persistant, accessible à tous les composants de la stack.
- ➕ Relancer l'indexation après une mise à jour des fiches ne revectorise que ce qui a changé.
- ➕ La recherche peut filtrer sur les métadonnées (rayon, Nutri-Score, `incomplete_data`, source).
- ➖ Un service de plus à surveiller, et un volume à sauvegarder (ou à reconstruire : ~11 min sur le GPU).
- ➖ Changer de modèle d'embeddings impose de tout reconstruire (`--rebuild`).
- ➖ L'indexation complète sur le processeur seul est longue (~1 h 20) : sur un poste sans GPU, la
  lancer une fois, puis profiter de l'indexation incrémentale.

Sources : documentation de Chroma (client HTTP, configuration `hnsw`) ; fiche du modèle
[qwen3-embedding](https://ollama.com/library/qwen3-embedding) ; mesures du 18/11/2026.
