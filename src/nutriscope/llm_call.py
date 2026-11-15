"""
Test rapide des modèles en ligne de commande (adresse du serveur et modèles lus dans l'environnement).

    python -m nutriscope.llm_call                          # état du serveur + un appel outillé
    python -m nutriscope.llm_call --photo data/photos/10_3608580065340_etiquette.jpg
    python -m nutriscope.llm_call --question "Quel est le Nutri-Score du Nutella ?"

Chaque appel affiche sa latence et ses tokens (chiffres pour l'ADR).
"""

from __future__ import annotations

import argparse
import json
import sys

from .assistant import Assistant, chat, llamacpp_status, load_config, make_client, ollama_status
from .scanner.image import to_data_url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--photo", help="lire un tableau nutritionnel avec le modèle de vision")
    parser.add_argument("--question", help="interroger l'assistant (catalogue PostgreSQL + outils)")
    args = parser.parse_args(argv)

    config = load_config()
    print(f"provider={config.provider} url={config.base_url} chat={config.chat_model} vision={config.vision_model}")
    if config.provider == "llamacpp":
        ready, models = llamacpp_status()
        if not ready:
            print("llama.cpp ne répond pas (ou charge encore le modèle) : docker compose ps, ou vérifiez LLAMACPP_HOST.")
            return 1
        print(f"llama.cpp prêt : {models}")
    if config.provider == "ollama":
        version, models = ollama_status()
        if version is None:
            print("Ollama ne répond pas : démarrez-le, ou vérifiez OLLAMA_HOST.")
            return 1
        print(f"Ollama {version}: {models}")
    client = make_client(config)

    if args.photo:
        data_url, size = to_data_url(args.photo)
        messages = [{"role": "user", "content": [
            {"type": "text", "text": "Recopie le tableau nutritionnel de cette photo."},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}]
        reply = chat(client, config, messages, model=config.vision_model, max_tokens=800)
        print(reply.content)
        print(f"{reply.latency_s:.1f} s, image {size[0]}x{size[1]}, "
              f"{reply.input_tokens} tokens en entrée, {reply.output_tokens} en sortie")

    if args.question:
        answer = Assistant.from_env(with_scanner=False, config=config, client=client).ask(args.question)
        answer.show()

    if not args.photo and not args.question:
        tool = {"type": "function", "function": {
            "name": "chercher_produit", "description": "Cherche un produit du catalogue.",
            "parameters": {"type": "object", "properties": {"nom": {"type": "string"}}}}}
        reply = chat(client, config, [{"role": "user", "content": "Quel est le Nutri-Score du Nutella ?"}],
                     tools=[tool], max_tokens=200)
        print("appels d'outil :", json.dumps(reply.tool_calls, ensure_ascii=False))
        print(f"{reply.latency_s:.1f} s, {reply.input_tokens} tokens in, {reply.output_tokens} out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
