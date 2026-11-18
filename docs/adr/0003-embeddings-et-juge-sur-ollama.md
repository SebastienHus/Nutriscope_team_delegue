# ADR 0003 — Les embeddings et le juge sont servis par Ollama : embeddings sur le processeur, juge sur le GPU une fois llama.cpp arrêté

Date : 18/11/2026 — Statut : **acceptée** — Complète l'ADR 0002 (llama.cpp reste le serveur de l'assistant et du scanner)

## Contexte

Le RAG (module 6.3) a besoin d'un modèle d'**embeddings**, et l'évaluation du TP 20 d'un **juge** qui note
les réponses de l'assistant par rapport aux réponses attendues. L'équipe retient :

- `qwen3-embedding:0.6b` pour les embeddings (vecteurs de dimension 1024, multilingue) ;
- un modèle juge spécialisé, entraîné à noter selon une grille.

Les deux sont servis par un second serveur, **Ollama** (service `ollama` de `compose.yml`). L'ADR 0002
écartait Ollama pour la **vision** (module de vision laissé sur le processeur) ; ni les embeddings ni le
juge ne lisent d'image, donc ce problème ne se pose pas ici.

La contrainte est la mémoire graphique : **8 Go**, dont ~6,9 Go libres une fois Windows et l'écran servis.
llama.cpp (Qwen3-VL-4B Q4_K_M + module de vision + contexte de 4 096 tokens) en occupe déjà ~4 Go.

## Ce qu'on a mesuré

Mesures du 18/11/2026, Quadro RTX 4000 (8 Go), Docker Desktop + WSL2, Ollama 0.30.10.

| Modèle | Taille du fichier | Mémoire chargée | Constat |
|---|---|---|---|
| Prometheus 2 7B Q4_K_M (premier choix) | 4,4 Go | > 5 Go | ne tient pas à côté de llama.cpp ; sur le processeur : **35 s** par note |
| Flow-Judge v0.1 3.8B Q4_K_M | 2,4 Go | 5,6 Go avec un contexte de 8 192 | tient seul sur le GPU (`100% GPU`) ; **4 s** par note une fois chargé |
| `qwen3-embedding:0.6b` (alias `num_gpu 0`) | 0,6 Go | 0 Go de mémoire graphique | `100% CPU` ; 16 fiches vectorisées en 5,6 s, chargement compris |

Essai de bout en bout sur 3 questions (une fiche produit, un produit inexistant, une question médicale) :
le juge donne 2, 4 et 5, des notes cohérentes avec les réponses. Note 2 sur la fiche produit : l'assistant
a répondu « pas dans le catalogue », parce que le lot de l'atelier n'est pas encore chargé dans la base.

## Options

1. **Tout sur le GPU en même temps** : impossible avec Prometheus 2 ; avec Flow-Judge, ~4 Go + ~4,5 Go
   (contexte réduit) dépassent encore les ~6,9 Go libres.
2. **Juge plus fortement quantifié** (Prometheus 2 en Q3_K_M, ~3,5 Go) : tient presque, mais le juge
   note moins finement, et c'est précisément son rôle.
3. **Juge par API** (secours prévu par l'ADR 0001) : rapide, mais payant, et il faut une clé d'API.
4. **Évaluation en deux passes et embeddings sur le processeur** : le juge ne sert pas à l'application,
   seulement à l'évaluation ; il peut donc tourner quand llama.cpp est arrêté.

## Décision

Option 4, avec **Flow-Judge v0.1 (3.8B)** à la place de Prometheus 2 (7B) :

- **Embeddings sur le processeur.** `ollama-init` crée l'alias `qwen3-embedding-cpu:0.6b`
  (`PARAMETER num_gpu 0`) ; le client `nutriscope.corpus.embeddings` l'utilise par défaut
  (`OLLAMA_EMBED_ALIAS`). Un modèle de 0,6B vectorise assez vite sans GPU, et l'assistant garde toute sa
  mémoire graphique pendant que le RAG tourne.
- **Évaluation en deux passes** (`python -m nutriscope.evaluation`) :
  1. `generate --version <nom>` : l'assistant (llama.cpp) répond aux questions de `eval/questions.csv` ;
     cette passe ne lit jamais les réponses attendues ;
  2. `docker compose stop llm`, puis `judge --version <nom>` : Flow-Judge note chaque réponse de 1 à 5
     (conforme à partir de 4), puis `docker compose start llm`. La passe refuse de démarrer tant que
     llama.cpp répond (`--allow-llm` pour passer outre).
- **Flow-Judge plutôt que Prometheus 2** : deux fois plus petit, entraîné au même type de grille de notation
  (sortie `<feedback>` puis `<score>`), et il laisse de la marge sur 8 Go. Il n'a pas d'entrée dans la
  bibliothèque Ollama : il est tiré du dépôt officiel `flowaicom/Flow-Judge-v0.1-GGUF` sur Hugging Face.
  Son prompt reprend le gabarit de sa fiche de modèle, en anglais (sa langue d'entraînement).
- **Contexte du juge réduit à 4 096 tokens** : un prompt fait ~1 500 tokens, et 8 192 coûtaient ~1 Go de plus.

## Conséquences

- ➕ L'assistant et les embeddings tournent ensemble sans se gêner : l'application n'a besoin que d'eux.
- ➕ Le juge a tout le GPU : ~4 s par note, soit quelques minutes pour les 30 questions du TP 20.
- ➕ La séparation des passes garantit que les réponses attendues n'atteignent jamais l'assistant.
- ➖ Une évaluation demande d'arrêter llama.cpp : l'application est indisponible pendant la passe 2.
- ➖ Vectoriser tout le catalogue (5 963 fiches) sur le processeur prend plusieurs minutes : acceptable
  pour une indexation faite une fois, à remesurer au module 6.3.
- ➖ Flow-Judge est plus petit que Prometheus 2 : ses notes sont à contrôler à la main sur un échantillon
  (TP 20), et la grille (`RUBRIC` dans `src/nutriscope/evaluation/judge.py`) à ajuster si besoin.

Sources : fiche du modèle [flowaicom/Flow-Judge-v0.1](https://huggingface.co/flowaicom/Flow-Judge-v0.1) ;
bibliothèque Ollama, [qwen3-embedding](https://ollama.com/library/qwen3-embedding) ; mesures du 18/11/2026.
