"""
RAG de NutriScope : découpage du corpus, indexation dans Chroma et recherche (ADR 0004).

- ``chunking`` : fiches produits (un morceau par fiche) et documents de référence (morceaux
  d'environ 800 caractères, sans couper une phrase ni une page) ;
- ``store`` : connexion au service chroma et ouverture des deux collections ``sheets`` et ``documents`` ;
- ``index`` : ``python -m nutriscope.rag.index`` vectorise (Ollama, processeur) et synchronise l'index ;
- ``search`` : ``python -m nutriscope.rag.search "question"`` renvoie les morceaux les plus proches.
"""
