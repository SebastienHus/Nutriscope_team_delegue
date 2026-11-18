"""
Évaluation de l'assistant en deux passes (TP 20, ADR 0003).

1. ``generate`` : l'assistant (llama.cpp) répond à chaque question de ``eval/questions.csv``, une
   nouvelle conversation par question ; les réponses vont dans ``results/eval/<version>_answers.csv``.
   Cette passe ne lit jamais les réponses attendues.
2. ``judge`` : une fois llama.cpp arrêté (``docker compose stop llm``), Flow-Judge (Ollama) note
   chaque réponse par rapport à la réponse et au comportement attendus ;
   ``results/eval/<version>_judged.csv`` et une ligne dans ``results/eval/history.csv``.

    python -m nutriscope.evaluation generate --version no_rag
    docker compose stop llm
    python -m nutriscope.evaluation judge --version no_rag
    docker compose start llm
"""
