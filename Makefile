# Façade mince sur la CLI : la logique vit dans src/nutriscope/pipeline.py.
# Sous Windows, `make` n'est pas installé par défaut : utiliser directement
#   python -m nutriscope.pipeline all
PY ?= python
export PYTHONUTF8 = 1

STEPS = load clean_data load_database parquet exports

.PHONY: install pipeline extrait $(STEPS) test clean clean-all

# Dans un venv activé : dépendances épinglées + package nutriscope en mode éditable
install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .

pipeline:
	$(PY) -m nutriscope.pipeline all

# Flux complet sur l'extrait (data/en.openfoodfacts.org.products.csv), pour le tableau des durées
extrait:
	$(PY) -m nutriscope.pipeline all --full

$(STEPS):
	$(PY) -m nutriscope.pipeline $@

test:
	$(PY) -m pytest -q

# Supprime UNIQUEMENT les sorties datées du pipeline (jamais les CSV sources de data/).
# Les exports figés ne sont supprimés que par clean-all.
clean:
	$(PY) -m nutriscope.pipeline purge

clean-all:
	$(PY) -m nutriscope.pipeline purge --include-exports