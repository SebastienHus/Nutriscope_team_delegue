"""
Brique « rayon d'un produit à partir de sa photo » (TP 17, point 5), appelée par l'API du TP 23.

    from nutriscope.image import ImageClassifier

    classifier = ImageClassifier.load()          # models/image_classifier/
    prediction = classifier.predict("photo.jpg")
    prediction.aisle       # "sodas", ou UNKNOWN sous le seuil
    prediction.confidence  # probabilité de la classe la plus probable

Le modèle et ses métadonnées (rayons, taille d'image, seuil, score de test) sont écrits
par `notebooks/dl_images.ipynb` via `image.models.save_bundle()`. Le prétraitement est
celui de l'entraînement (`image.data.load_image`), pour que l'application voie les
photos exactement comme le modèle les a vues.

TensorFlow n'est importé qu'au chargement du modèle : la règle de décision
(`decide()`) se teste sans lui.

Photos : CC BY-SA, contributeurs Open Food Facts.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..options import ROOT_PATH

MODELS_PATH = ROOT_PATH / "models"
DEFAULT_MODEL_DIR = MODELS_PATH / "image_classifier"
MODEL_FILENAME = "model.keras"
METADATA_FILENAME = "metadata.json"

UNKNOWN = "unknown"  # réponse « je ne sais pas »

# Clés obligatoires de metadata.json
REQUIRED_METADATA = ("aisles", "image_size", "threshold")


@dataclass(frozen=True)
class Prediction:
    """Réponse de la brique pour une photo."""

    aisle: str  # rayon prédit, ou UNKNOWN si la confiance est sous le seuil
    confidence: float  # probabilité du rayon le plus probable (même sous le seuil)
    best_guess: str  # rayon le plus probable, même quand la réponse est UNKNOWN
    probabilities: dict[str, float] = field(default_factory=dict)

    @property
    def is_known(self) -> bool:
        return self.aisle != UNKNOWN

    def to_dict(self) -> dict:
        """Forme JSON-sérialisable, pour l'API."""
        return {
            "aisle": self.aisle,
            "confidence": round(self.confidence, 4),
            "best_guess": self.best_guess,
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
        }


def decide(probabilities, aisles, threshold: float) -> Prediction:
    """Règle de décision : le rayon le plus probable si sa probabilité atteint le seuil,
    sinon UNKNOWN. Fonction pure, sans TensorFlow."""
    probabilities = np.asarray(probabilities, dtype=float).ravel()
    if probabilities.shape[0] != len(aisles):
        raise ValueError(f"{probabilities.shape[0]} probabilités pour {len(aisles)} rayons")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"seuil hors de [0, 1] : {threshold}")
    best = int(np.argmax(probabilities))
    confidence = float(probabilities[best])
    return Prediction(
        aisle=aisles[best] if confidence >= threshold else UNKNOWN,
        confidence=confidence,
        best_guess=aisles[best],
        probabilities=dict(zip(aisles, map(float, probabilities))),
    )


def read_metadata(model_dir: os.PathLike = DEFAULT_MODEL_DIR) -> dict:
    """Lit et valide metadata.json."""
    path = Path(model_dir) / METADATA_FILENAME
    metadata = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_METADATA if key not in metadata]
    if missing:
        raise KeyError(f"{path} : clés manquantes {missing}")
    return metadata


class ImageClassifier:
    """Modèle Keras + rayons + taille d'image + seuil, chargés ensemble."""

    def __init__(self, model, aisles, image_size, threshold: float, metadata: dict | None = None):
        self.model = model
        self.aisles = list(aisles)
        self.image_size = tuple(image_size)
        self.threshold = float(threshold)
        self.metadata = metadata or {}

    @classmethod
    def load(cls, model_dir: os.PathLike = DEFAULT_MODEL_DIR) -> "ImageClassifier":
        import tensorflow as tf  # import tardif : lourd, inutile pour decide()

        metadata = read_metadata(model_dir)
        model = tf.keras.models.load_model(Path(model_dir) / MODEL_FILENAME)
        return cls(model, metadata["aisles"], metadata["image_size"], metadata["threshold"], metadata)

    def predict_proba(self, image_path: os.PathLike) -> np.ndarray:
        """Probabilités par rayon (dans l'ordre de self.aisles) pour une photo."""
        from .data import load_image

        image = load_image(str(image_path), self.image_size)
        return self.model.predict(image[None, ...], verbose=0)[0]

    def predict(self, image_path: os.PathLike) -> Prediction:
        if not Path(image_path).is_file():
            raise FileNotFoundError(image_path)
        return decide(self.predict_proba(image_path), self.aisles, self.threshold)
