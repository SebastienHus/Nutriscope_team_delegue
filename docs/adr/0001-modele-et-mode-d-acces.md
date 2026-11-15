# ADR 0001 — L'assistant tourne sur un modèle local servi par Ollama (`qwen3:8b`), une API compatible OpenAI restant possible par configuration

Date : 15/11/2026 — Statut : **proposée** (passe à « acceptée » une fois les mesures ci-dessous remplies)

> **Modifiée par l'[ADR 0002](0002-llama-cpp-au-lieu-d-ollama.md)** : le modèle local est désormais servi par
> **llama.cpp** et non par Ollama, qui lisait les images sur le processeur avec une carte de 8 Go ; un seul
> modèle (`qwen3-vl-4b-instruct`) sert l'assistant et le scanner. Le choix du local, et l'API en secours, tiennent.

## Contexte

NutriScope veut un assistant qui répond sur les produits **à partir du catalogue de l'équipe** (base
PostgreSQL, données Open Food Facts). Le modèle doit savoir appeler un outil (`chercher_produit`), puis un
modèle de vision lira les étiquettes (atelier scanner). Contraintes :

- formation sur postes individuels, parfois sans carte graphique ; pas de budget récurrent ;
- questions d'utilisateurs : pas de données de santé sollicitées (refusées), mais des habitudes alimentaires ;
- une clé d'API ne doit jamais entrer dans le dépôt ;
- la même stack doit tourner en local (notebooks) et dans Docker (`compose.yml`, service `llm`).

## Options

1. **Modèle local avec Ollama** : `qwen3:8b` pour l'assistant, `qwen3-vl:4b-instruct` pour la vision.
2. **API commerciale** (OpenAI, Anthropic…) : modèles plus capables, facturés au token, hébergés hors UE.
3. **API hébergée en Europe** (Mistral, ou OpenRouter avec un fournisseur européen) : facturée au token,
   données traitées dans l'UE.

Les trois s'appellent avec le **même client** (point d'accès compatible OpenAI) : seul `.env` change
(`LLM_PROVIDER`, `OLLAMA_HOST` ou `API_BASE_URL` / `API_KEY`, voir `src/nutriscope/assistant/config.py`).

## Critères

| Critère | Local (Ollama, `qwen3:8b`) | API commerciale | API hébergée en Europe |
|---|---|---|---|
| Coût | 0 € par appel (matériel déjà là) | au token, croît avec l'usage | au token, souvent moins cher |
| Latence d'un appel outillé | **mesurée : ___ s** (médiane, notebook `llm.ipynb` §2) | réseau + file d'attente, à mesurer | idem |
| Confidentialité | rien ne sort du poste | questions envoyées hors UE | questions traitées dans l'UE |
| Qualité de l'appel d'outils | correcte sur nos questions (démonstration §3) ; risque de valeurs inventées | meilleure | variable selon le modèle |
| Dépendance | aucune après le téléchargement | fournisseur, clé, quota | fournisseur, clé, quota |

Mesures faites par l'équipe (notebook `notebooks/llm.ipynb`, section 2 ; poste : ___) :

| Mesure | Valeur |
|---|---|
| Latence médiane d'un appel outillé (`qwen3:8b`, 5 essais, hors 1er) | ___ s |
| Premier appel (chargement du modèle) | ___ s |
| Tokens d'entrée d'un appel (prompt système + outil + question) | ___ |
| Latence médiane d'une question complète (2 appels + outil, §5) | ___ s |

Repère de prix pour le secours par API (brief de l'atelier, relevé du 11/11/2026, OpenRouter) :
`qwen/qwen3-vl-8b-instruct` 0,25 $ / 0,75 $ par million de tokens (entrée / sortie).

## Décision

Option 1 : **modèle local avec Ollama**, `qwen3:8b` pour l'assistant (raisonnement désactivé :
`LLM_REASONING_EFFORT=none`, sinon le budget de tokens part dans la réflexion) et `qwen3-vl:4b-instruct` pour
le scanner, à température 0. Raisons : coût nul pour la formation, aucune question d'utilisateur ne quitte le
poste, et la qualité suffit **parce que les garde-fous ne reposent pas sur le modèle** : arguments validés
avant exécution, refus médical en code, relecture des nombres en code. L'adresse du serveur vient de la variable
d'Ollama `OLLAMA_HOST` (`http://localhost:11434` par défaut, `http://llm:11434` dans Docker).

L'API reste un **secours configuré, pas codé** : `LLM_PROVIDER=api` + `API_BASE_URL`, `API_KEY` (dans `.env`,
ignoré par Git), `API_CHAT_MODEL`, et les prix pour que chaque appel affiche son coût.

## Conséquences

- ➕ Coût marginal nul, confidentialité totale, démonstration possible hors réseau.
- ➕ Changer de modèle ou passer à l'API = modifier `.env`, sans toucher au code.
- ➖ Latence de plusieurs secondes par appel sur un portable sans GPU ; une question qui demande deux produits
  enchaîne trois appels au modèle.
- ➖ Un modèle de 8 milliards de paramètres invente plus volontiers des valeurs ou calcule des écarts : la
  relecture en code les écarte, au prix d'un tour de plus ou d'une réponse de repli moins riche.
- ➖ 5 à 6 Go de modèle par poste, et une version d'Ollama récente (≥ 0.12.7) pour la vision.
- À remettre en cause si la latence mesurée dépasse ce qu'accepte l'application (TP 23), ou si la part de
  réponses de repli devient trop grande sur les questions de démonstration.

Données : © Open Food Facts contributors — ODbL.
