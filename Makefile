# Façade sur la CLI : toute la logique vit dans nutriscope/pipeline.py.
# Sous Windows, `make` n'est souvent pas installé : utilisez directement
#   python -m nutriscope.pipeline all
PY ?= python
export PYTHONUTF8 = 1

.PHONY: pipeline pipeline-sans-base charger nettoyer charger_base parquet exports status clean test

pipeline:
	$(PY) -m nutriscope.pipeline all

pipeline-sans-base:
	$(PY) -m nutriscope.pipeline all --skip charger_base

charger nettoyer charger_base parquet exports:
	$(PY) -m nutriscope.pipeline $@

status:
	$(PY) -m nutriscope.pipeline status

clean:
	$(PY) -m nutriscope.pipeline clean

test:
	$(PY) -m pytest -q
