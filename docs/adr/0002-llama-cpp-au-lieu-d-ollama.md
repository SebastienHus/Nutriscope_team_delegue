# ADR 0002 — Le modèle est servi par llama.cpp et non plus par Ollama, qui lit les images sur le processeur avec une carte de 8 Go

Date : 15/11/2026 — Statut : **acceptée** — Modifie l'ADR 0001 (le serveur du modèle ; le reste tient)

## Contexte

L'ADR 0001 retient un modèle local servi par Ollama (service `llm` de `compose.yml`). Au premier passage
complet du scanner d'étiquettes (`python scan_tools/measure_scanner.py`, 22 photos), la lecture était juste
mais beaucoup trop lente pour l'application : **54,8 s par photo en moyenne**, de 16 à 79 s, soit 20 minutes
pour une mesure.

Poste de mesure : RTX 3070 (8 Go de mémoire graphique, dont ~6,9 Go libres une fois Windows et l'écran
servis), Docker Desktop + WSL2, surcouche `compose.gpu.yml`, Ollama 0.30.10.

## Ce qu'on a trouvé, étape par étape

| Étape | Observation | Conclusion |
|---|---|---|
| `qwen3-vl:8b-instruct` | `ollama ps` : `31%/69% CPU/GPU` | le 8B ne tient pas entier dans 8 Go : un tiers tourne sur le processeur |
| `qwen3-vl:4b-instruct` | `100% GPU`, mais encore ~36 s par photo | le modèle tient, la lenteur est ailleurs |
| Journaux d'Ollama (4B) | `prompt eval` : 35 s pour 1 059 tokens (**30 tokens/s**) ; génération : 77 tokens/s | c'est la lecture de l'entrée qui est lente, pas la réponse |
| Même modèle, question sans image | `prompt eval` : **3 120 tokens/s** | le GPU traite bien le texte : le problème vient de l'image |
| Journal de chargement | `disabling multimodal projector offload reason=limited-vram`, puis `CLIP using CPU backend` | **Ollama met le module de vision (mmproj) sur le processeur** |

La cause est un comportement d'Ollama, pas un vrai manque de mémoire : le chargement annonçait plus de 4 Go
libres après le modèle. Dans les versions 0.30.x, Ollama décide de garder le module de vision sur le
processeur quand la carte n'a pas assez de mémoire selon son estimation ; d'après la discussion du ticket
[ollama#16496](https://github.com/ollama/ollama/issues/16496), la réserve prévue pour ce module est codée en
dur (10 Go), si bien qu'une carte de 8 Go tombe toujours dessous. Aucune variable d'environnement ne force le
module sur le GPU ([ollama#16419](https://github.com/ollama/ollama/issues/16419)) ; le ticket est ouvert et la
seule correction proposée (PR #16568) n'est pas fusionnée au 15/11/2026.

## Ce qu'on a essayé avant de changer de serveur

- **Réduire la mémoire du contexte** (`LLM_CTX=4096`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`) :
  aucun effet sur le module de vision. Seul `LLM_CTX=4096` est gardé (nos lectures font ~1 600 tokens).
- **Revenir à Ollama 0.24.0**, conseillé dans le ticket : le moteur plante sur `qwen3-vl` dès la première
  image (`llama runner terminated`, `exit status 2`) ; toutes les photos sortent `illisible`.

Il n'existe donc pas de version d'Ollama qui fasse à la fois tourner `qwen3-vl` et garder sa vision sur le GPU
d'une carte de 8 Go.

## Options

1. **Garder Ollama** et accepter ~36 s (4B) à ~55 s (8B) par photo.
2. **Passer par une API** (secours prévu par l'ADR 0001) : rapide, mais payant et les photos quittent le poste.
3. **Servir le modèle avec llama.cpp** (`llama-server`), le moteur qu'Ollama utilise lui-même : par défaut,
   il met le module de vision sur le GPU, et il parle la même API compatible OpenAI.

## Décision

Option 3. Le service `llm` de `compose.yml` est un `llama-server` (`ghcr.io/ggml-org/llama.cpp`, image CUDA
dans `compose.gpu.yml`), et le job `llm-init` télécharge depuis Hugging Face le modèle officiel
`Qwen/Qwen3-VL-4B-Instruct-GGUF` en `Q4_K_M` et son module de vision en F16 (~3,3 Go, une seule fois).
Côté code, le fournisseur `llamacpp` devient celui par défaut (`LLM_PROVIDER`, `LLAMACPP_HOST`, `LLM_MODEL` :
`src/nutriscope/assistant/config.py`). Ollama reste utilisable par configuration (`LLM_PROVIDER=ollama`).

Réglages repris d'Ollama pour garder des mesures comparables : contexte de 4 096 tokens, `--image-min-tokens
1024` (même découpage de l'image), gabarit du modèle (`--jinja`, nécessaire à l'appel d'outils).

## Résultat mesuré

Même lot de 22 photos, même script (`results/history.csv`) :

| Version | Serveur et modèle | Justesse | Inventées | Latence moyenne / max par photo | Tokens entrée / sortie |
|---|---|---|---|---|---|
| `palier1` | Ollama, `qwen3-vl:8b-instruct` (vision sur le processeur) | 100 % | 0 | 54,8 s / 79,2 s | 1 455 / 161 |
| *(2 photos, non enregistré)* | Ollama, `qwen3-vl:4b-instruct` (vision sur le processeur) | — | — | ~36 s | ~1 420 / ~155 |
| `llamacpp_4b` | llama.cpp, Qwen3-VL-4B-Instruct Q4_K_M (vision sur le GPU) | **100 %** | **0** | **3,6 s / 8,8 s** | 1 450 / 156 |

Le scanner est **environ 15 fois plus rapide**, sans perte de justesse ; une mesure complète passe de
20 minutes à moins d'une minute et demie.

## Conséquences

- ➕ Lecture d'une photo en ~3 s sur le poste : utilisable dans l'application (TP 23).
- ➕ Même client, même API compatible OpenAI : le scanner et l'assistant n'ont pas changé, seule la configuration.
- ➕ `llama-server --metrics` : Prometheus surveille de nouveau le serveur du modèle (`llm:8080/metrics`).
- ➖ **Un seul modèle servi**, pour l'assistant comme pour le scanner (`qwen3-vl-4b-instruct`, au lieu de
  `qwen3:8b` prévu par l'ADR 0001 pour l'assistant). Le vote entre deux modèles (`SCANNER_MODELS`, version
  `deux_modeles`) demanderait un second serveur.
- ➖ Le modèle 8B (≈ 5 Go + 1 Go de module de vision) reste trop juste pour 8 Go de mémoire graphique.
- ➖ L'image `server-cuda-b11434` est figée : à mettre à jour à la main (`LLAMACPP_VERSION`).
- À revoir quand Ollama aura corrigé le ticket #16496, si l'équipe veut revenir à un seul outil pour
  télécharger et servir les modèles.

Sources : [ollama#16496](https://github.com/ollama/ollama/issues/16496),
[ollama#16419](https://github.com/ollama/ollama/issues/16419),
[ollama#16617](https://github.com/ollama/ollama/issues/16617) ; journaux et mesures du 15/11/2026.
