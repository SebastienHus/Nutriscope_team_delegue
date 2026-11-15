"""
Un seul client pour les modèles locaux (llama.cpp, Ollama) et distants (API) : le point d'accès compatible OpenAI.

``chat`` fait un appel et le mesure (latence, tokens, coût) ; il rend un ``ModelReply`` dont le
``message`` peut être ajouté tel quel à l'historique de la conversation.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .config import LLMConfig, llamacpp_host, ollama_host

THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


@dataclass
class ModelReply:
    content: str
    tool_calls: list[dict[str, Any]]          # [{"id", "name", "arguments"}], arguments = texte JSON brut
    message: dict[str, Any]                   # message de l'assistant à remettre dans l'historique
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    finish_reason: str = ""
    cost: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


def make_client(config: LLMConfig):
    from openai import OpenAI

    return OpenAI(base_url=config.base_url, api_key=config.api_key, timeout=config.timeout, max_retries=1)


def chat(client, config: LLMConfig, messages: list[dict[str, Any]], *, model: str | None = None,
         tools: list[dict[str, Any]] | None = None, temperature: float = 0.0, max_tokens: int = 600,
         response_format: dict[str, Any] | None = None) -> ModelReply:
    """Un appel mesuré. Les exceptions du client (serveur arrêté, délai dépassé) sont laissées à l'appelant."""
    options: dict[str, Any] = {}
    if config.reasoning_effort:
        options["reasoning_effort"] = config.reasoning_effort
    if tools:
        options["tools"] = tools
    if response_format:
        options["response_format"] = response_format
    model = model or config.chat_model
    start = time.perf_counter()
    response = client.chat.completions.create(model=model, messages=messages, temperature=temperature,
                                              max_tokens=max_tokens, **options)
    latency = time.perf_counter() - start

    choice = response.choices[0]
    raw = choice.message
    content = THINK_BLOCK.sub("", raw.content or "").strip()
    calls = [{"id": call.id, "name": call.function.name, "arguments": call.function.arguments}
             for call in (raw.tool_calls or [])]
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = [{"id": c["id"], "type": "function",
                                  "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]
    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    return ModelReply(content=content, tool_calls=calls, message=message, model=model,
                      input_tokens=input_tokens, output_tokens=output_tokens, latency_s=latency,
                      finish_reason=choice.finish_reason or "", cost=config.cost(input_tokens, output_tokens))


def describe_error(exc: Exception) -> str:
    """Erreur du client en une ligne lisible : « NotFoundError: model 'qwen3:8b' not found »."""
    body = getattr(exc, "body", None)
    message = body.get("message") if isinstance(body, dict) else None
    text = message or str(exc) or ""
    text = text.split("\n")[0][:200]
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def llamacpp_status(timeout: float = 5.0) -> tuple[bool, list[str]]:
    """(serveur prêt, modèles servis) ; (False, []) si le serveur ne répond pas ou charge encore."""
    base = llamacpp_host()
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=timeout) as response:
            ready = response.status == 200
        with urllib.request.urlopen(f"{base}/v1/models", timeout=timeout) as response:
            models = [model["id"] for model in json.load(response).get("data", [])]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return False, []
    return ready, models


def ollama_status(timeout: float = 5.0) -> tuple[str | None, list[str]]:
    """(version d'Ollama, modèles installés), ou (None, []) si le serveur ne répond pas."""
    base = ollama_host()
    try:
        with urllib.request.urlopen(f"{base}/api/version", timeout=timeout) as response:
            version = json.load(response).get("version")
        with urllib.request.urlopen(f"{base}/api/tags", timeout=timeout) as response:
            models = [model["name"] for model in json.load(response).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return None, []
    return version, models
