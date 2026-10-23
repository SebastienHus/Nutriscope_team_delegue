# Façade mince sur la CLI : la logique vit dans src/nutriscope/pipeline.py.
# Sous Windows, `make` n'est pas installé par défaut : utiliser directement
#   python -m nutriscope.pipeline all
PY ?= python
ARGS ?=
export PYTHONUTF8 = 1

STEPS = load clean_data load_database parquet exports

.PHONY: install pipeline extrait $(STEPS) test clean clean-all

# Dans un venv activé : dépendances épinglées + package nutriscope en mode éditable
install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .

pipeline:
	$(PY) -m nutriscope.pipeline all $(ARGS)

# Flux complet sur l'extrait (data/en.openfoodfacts.org.products.csv), pour le tableau des durées
extrait:
	$(PY) -m nutriscope.pipeline all --full $(ARGS)

$(STEPS):
	$(PY) -m nutriscope.pipeline $@ $(ARGS)

test:
	$(PY) -m pytest -q $(ARGS)

# Supprime UNIQUEMENT les sorties datées du pipeline (jamais les sources de data/),
# pour la source courante : l'échantillon, ou l'extrait complet avec ARGS=--full.
# Les exports figés ne sont supprimés qu'avec ARGS=--include-exports.
clean:
	$(PY) -m nutriscope.pipeline purge $(ARGS)

# Même chose pour toutes les sources
clean-all:
	$(PY) -m nutriscope.pipeline purge -a $(ARGS)