"""
Tests de la brique image (TP 17, point 5).

- La règle de décision (`decide`) se teste sans TensorFlow ni photos.
- Le test de bout en bout charge le vrai modèle sauvegardé et une vraie photo du jeu de
  test : il est sauté tant que le notebook n'a pas produit `models/image_classifier/`
  et que les photos ne sont pas téléchargées.
"""

import json

import numpy as np
import pytest

from nutriscope.image.classifier import (
    DEFAULT_MODEL_DIR,
    METADATA_FILENAME,
    MODEL_FILENAME,
    UNKNOWN,
    decide,
    read_metadata,
)

AISLES = ["biscuits", "chocolats", "sodas"]


def test_decide_answers_above_threshold():
    prediction = decide([0.1, 0.8, 0.1], AISLES, threshold=0.6)
    assert prediction.aisle == "chocolats"
    assert prediction.is_known
    assert prediction.confidence == pytest.approx(0.8)


def test_decide_says_unknown_below_threshold():
    prediction = decide([0.4, 0.35, 0.25], AISLES, threshold=0.6)
    assert prediction.aisle == UNKNOWN
    assert not prediction.is_known
    assert prediction.best_guess == "biscuits"  # le meilleur candidat reste disponible


def test_decide_threshold_is_inclusive():
    assert decide([0.6, 0.3, 0.1], AISLES, threshold=0.6).aisle == "biscuits"


def test_decide_zero_threshold_always_answers():
    assert decide([0.34, 0.33, 0.33], AISLES, threshold=0.0).is_known


def test_decide_rejects_inconsistent_inputs():
    with pytest.raises(ValueError):
        decide([0.5, 0.5], AISLES, threshold=0.5)
    with pytest.raises(ValueError):
        decide([0.2, 0.3, 0.5], AISLES, threshold=1.5)


def test_prediction_to_dict_is_json_serializable():
    payload = decide(np.array([0.1, 0.2, 0.7], dtype=np.float32), AISLES, threshold=0.5).to_dict()
    assert json.loads(json.dumps(payload))["aisle"] == "sodas"


def test_read_metadata_requires_keys(tmp_path):
    (tmp_path / METADATA_FILENAME).write_text(json.dumps({"aisles": AISLES}), encoding="utf-8")
    with pytest.raises(KeyError):
        read_metadata(tmp_path)


# ----------------------------------------------------------------------------
# Bout en bout : vrai modèle, vraie photo
# ----------------------------------------------------------------------------

needs_model = pytest.mark.skipif(
    not (DEFAULT_MODEL_DIR / MODEL_FILENAME).exists(),
    reason="modèle non entraîné : exécuter notebooks/dl_images.ipynb",
)


@needs_model
def test_saved_model_classifies_a_real_photo():
    from nutriscope.image import ImageClassifier
    from nutriscope.image.data import SPLIT_FILE, TEST, load_split

    if not SPLIT_FILE.exists():
        pytest.skip("photos non téléchargées (data/images/split.csv absent)")
    classifier = ImageClassifier.load()
    split = load_split()
    path = split.loc[split["split"] == TEST, "path"].iloc[0]

    prediction = classifier.predict(path)

    assert prediction.aisle in [*classifier.aisles, UNKNOWN]
    assert 0.0 <= prediction.confidence <= 1.0
    assert sum(prediction.probabilities.values()) == pytest.approx(1.0, abs=1e-3)
    assert (prediction.confidence >= classifier.threshold) == prediction.is_known


@needs_model
def test_missing_photo_raises():
    from nutriscope.image import ImageClassifier

    with pytest.raises(FileNotFoundError):
        ImageClassifier.load().predict("introuvable.jpg")
