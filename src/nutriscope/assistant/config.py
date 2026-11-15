"""
Configuration des modèles : tout vient des variables d'environnement (ou du fichier ``.env``).

En local (par défaut), le serveur llama.cpp de la stack Docker (service ``llm``), avec ``LLM_PROVIDER=llamacpp`` :

| Variable               | Défaut                    | Rôle                                          |
| ---------------------- | ------------------------- | --------------------------------------------- |
| `LLAMACPP_HOST`        | `http://localhost:8081`   | serveur llama.cpp (le suffixe `/v1` est ajouté) |
| `LLM_MODEL`            | `qwen3-vl-4b-instruct`    | modèle servi, pour l'assistant et le scanner  |
| `LLM_TIMEOUT`          | `300`                     | secondes par appel                            |

Ollama reste possible avec ``LLM_PROVIDER=ollama`` et la variable d'Ollama pour l'adresse du serveur :

| Variable               | Défaut                    | Rôle                                          |
| ---------------------- | ------------------------- | --------------------------------------------- |
| `OLLAMA_HOST`          | `http://localhost:11434`  | serveur Ollama (le suffixe `/v1` est ajouté)  |
| `OLLAMA_CHAT_MODEL`    | `qwen3:8b`                | modèle de l'assistant (appel d'outils)        |
| `OLLAMA_VISION_MODEL`  | `qwen3-vl:4b-instruct`    | modèle du scanner d'étiquettes                |
| `LLM_REASONING_EFFORT` | `none`                    | coupe la réflexion de qwen3 ("" pour la garder) |
| `LLM_TIMEOUT`          | `300`                     | secondes par appel                            |

API distante (compatible OpenAI : OpenRouter, Mistral...), avec ``LLM_PROVIDER=api`` :
`API_BASE_URL`, `API_KEY` (jamais dans le code ni dans le dépôt), `API_CHAT_MODEL`,
`API_VISION_MODEL`, `API_PRICE_INPUT` et `API_PRICE_OUTPUT` (dollars par million de tokens).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..options import load_env_file

DEFAULT_LLAMACPP_HOST = "http://localhost:8081"
DEFAULT_LLAMACPP_MODEL = "qwen3-vl-4b-instruct"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_CHAT_MODEL = "qwen3:8b"
DEFAULT_VISION_MODEL = "qwen3-vl:4b-instruct"


class ConfigError(RuntimeError):
    """Une variable obligatoire manque."""


def llamacpp_host() -> str:
    """Adresse du serveur llama.cpp lue dans LLAMACPP_HOST (schéma facultatif)."""
    host = (os.getenv("LLAMACPP_HOST") or DEFAULT_LLAMACPP_HOST).strip().rstrip("/")
    if "://" not in host:
        host = f"http://{host}"
    return host.removesuffix("/v1")


def ollama_host() -> str:
    """Adresse du serveur lue dans OLLAMA_HOST, qu'Ollama accepte aussi sans schéma ("0.0.0.0:11434")."""
    host = (os.getenv("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).strip().rstrip("/")
    if "://" not in host:
        host = f"http://{host}"
    # 0.0.0.0 est une adresse d'écoute du serveur ; un client le joint sur localhost
    return host.replace("://0.0.0.0", "://localhost")


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str               # point d'accès compatible OpenAI
    api_key: str
    chat_model: str
    vision_model: str
    price_input: float = 0.0    # dollars par million de tokens
    price_output: float = 0.0
    reasoning_effort: str | None = None
    timeout: float = 300.0

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.price_input + output_tokens * self.price_output) / 1_000_000


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"{name} is not set (LLM_PROVIDER=api): add it to .env")
    return value


def load_config() -> LLMConfig:
    load_env_file()
    provider = (os.getenv("LLM_PROVIDER") or "llamacpp").strip().lower()
    timeout = float(os.getenv("LLM_TIMEOUT") or 300)
    if provider == "llamacpp":
        model = os.getenv("LLM_MODEL") or DEFAULT_LLAMACPP_MODEL   # --alias du serveur : un seul modèle
        return LLMConfig(
            provider="llamacpp",
            base_url=f"{llamacpp_host()}/v1",
            api_key="llamacpp",                     # le serveur l'ignore, mais le client en exige une
            chat_model=model,
            vision_model=model,
            timeout=timeout,
        )
    if provider == "ollama":
        effort = os.getenv("LLM_REASONING_EFFORT", "none")
        return LLMConfig(
            provider="ollama",
            base_url=f"{ollama_host()}/v1",
            api_key="ollama",                       # Ollama l'ignore, mais le client en exige une
            chat_model=os.getenv("OLLAMA_CHAT_MODEL") or DEFAULT_CHAT_MODEL,
            vision_model=os.getenv("OLLAMA_VISION_MODEL") or DEFAULT_VISION_MODEL,
            reasoning_effort=effort or None,
            timeout=timeout,
        )
    if provider == "api":
        return LLMConfig(
            provider="api",
            base_url=_required("API_BASE_URL"),
            api_key=_required("API_KEY"),
            chat_model=_required("API_CHAT_MODEL"),
            vision_model=os.getenv("API_VISION_MODEL") or _required("API_CHAT_MODEL"),
            price_input=float(os.getenv("API_PRICE_INPUT") or 0),
            price_output=float(os.getenv("API_PRICE_OUTPUT") or 0),
            reasoning_effort=os.getenv("LLM_REASONING_EFFORT") or None,
            timeout=timeout,
        )
    raise ConfigError(f"LLM_PROVIDER={provider!r}: expected 'llamacpp', 'ollama' or 'api'")
