"""
Passe 1 : l'assistant répond à chaque question (llama.cpp doit tourner).

Une nouvelle conversation par question (sans historique), à la température du fichier de
comportement de l'assistant (0). Seules les colonnes ``id``, ``type`` et ``question`` du jeu
d'évaluation sont lues.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .common import answers_path, load_questions, write_csv

ANSWER_COLUMNS = ["id", "type", "question", "answer", "tools_called", "outcome", "model",
                  "latency_s", "input_tokens", "output_tokens", "generated_at"]


def tools_called(answer) -> str:
    """Liste JSON de {"name", "arguments"} : ce que l'assistant a demandé aux outils, dans l'ordre."""
    return json.dumps([{"name": trace.name, "arguments": trace.arguments} for trace in answer.tool_calls],
                      ensure_ascii=False)


def generate(assistant, questions: list[dict[str, str]], output: Path, verbose: bool = True) -> list[dict]:
    rows = []
    for index, item in enumerate(questions, start=1):
        answer = assistant.ask(item["question"])  # sans historique : une conversation par question
        row = {
            **item,
            "answer": answer.text,
            "tools_called": tools_called(answer),
            "outcome": answer.outcome,
            "model": answer.model,
            "latency_s": round(answer.latency_s, 2),
            "input_tokens": answer.input_tokens,
            "output_tokens": answer.output_tokens,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        rows.append(row)
        write_csv(output, rows, ANSWER_COLUMNS)  # écrit après chaque question : un plantage garde le reste
        if verbose:
            print(f"[{index}/{len(questions)}] {item['id']} {answer.outcome} {answer.latency_s:.1f} s")
    return rows


def run(args) -> int:
    from ..assistant import Assistant

    questions = load_questions(args.questions, with_truth=False, ids=args.ids)
    if not questions:
        print("No question to ask.")
        return 1
    output = answers_path(args.results, args.version)
    if output.exists() and not args.force:
        print(f"{output} already exists: a measured version never changes (--force to overwrite)")
        return 1
    assistant = Assistant.from_env(with_scanner=False)
    rows = generate(assistant, questions, output)
    errors = sum(row["outcome"].startswith("error") for row in rows)
    print(f"{len(rows)} answers written to {output}" + (f" ({errors} error(s))" if errors else ""))
    print("Next: docker compose stop llm, then python -m nutriscope.evaluation judge "
          f"--version {args.version}")
    return 1 if errors else 0
