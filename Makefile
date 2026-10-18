# Façade mince sur la CLI : la logique vit dans nutriscope/pipeline.py.
# Sous Windows, `make` n'est pas installé par défaut : utiliser directement
#   python -m nutriscope.pipeline all
PY ?= python
export PYTHONUTF8 = 1

.PHONY: pipeline load clean_data load_database parquet exports test clean docker docker-test

venv:
	$(PY) -m venv .venv
	.venv/Scripts/Activate.ps1
	$(PY) install -r requirements.txt

pipeline:
	$(PY) -m nutriscope.pipeline all

load clean_data load_database parquet exports:
	$(PY) -m nutriscope.pipeline $@

test:
	$(PY) -m pytest -q

# Supprime UNIQUEMENT les dossiers produits par le pipeline (jamais les CSV de data/ à la racine).
# Les exports figés ne sont supprimés qu'avec --include-exports.
clean:
	$(PY) -m nutriscope.pipeline clean

docker:
	docker compose run --rm --build pipeline all

docker-test:
	docker compose run --rm --entrypoint python pipeline -m pytest -q
