"""``python -m nutriscope.evaluation generate|judge --version <nom>`` : voir la documentation du package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..options import load_env_file
from .common import QUESTIONS_PATH, RESULTS_DIR


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m nutriscope.evaluation",
                                     description="Évaluation de l'assistant en deux passes.")
    parser.add_argument("pass_name", choices=["generate", "judge"], help="passe à lancer")
    parser.add_argument("--version", required=True, help="nom de la version mesurée, par exemple no_rag, rag_v1")
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH, help="jeu d'évaluation (CSV)")
    parser.add_argument("--results", type=Path, default=RESULTS_DIR, help="dossier des résultats")
    parser.add_argument("--ids", nargs="+", help="generate : seulement ces id de questions")
    parser.add_argument("--force", action="store_true", help="generate : écrase une version existante")
    parser.add_argument("--judge-model", help="judge : modèle Ollama (par défaut : OLLAMA_JUDGE_MODEL)")
    parser.add_argument("--allow-llm", action="store_true", help="judge : lance même si llama.cpp tourne")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_env_file()
    if args.pass_name == "generate":
        from .generate import run
    else:
        from .judge import run
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
