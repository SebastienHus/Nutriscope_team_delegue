"""
Modèles du TP 17 : CNN de référence entraîné de zéro, transfert MobileNetV2
(extraction de features puis fine-tuning), sauvegarde du modèle retenu.

Entrées : images float32 en [0, 255] (voir `data.load_image`). Chaque modèle porte
sa normalisation, et l'augmentation est faite par des couches Keras actives seulement
pendant `fit` : à l'inférence (validation, test, application) elles sont neutres.

Cibles : entiers 0..K-1 (perte `sparse_categorical_crossentropy`).
"""

import json
import os
from datetime import date
from pathlib import Path

import tensorflow as tf
from tensorflow.keras import callbacks, layers, models

from .classifier import DEFAULT_MODEL_DIR, METADATA_FILENAME, MODEL_FILENAME
from ..options import RANDOM_SEED

LOSS = "sparse_categorical_crossentropy"
METRICS = ["accuracy"]


def compile_model(model, learning_rate: float):
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate), loss=LOSS, metrics=METRICS)
    return model


def early_stopping(patience: int = 4):
    """Même critère pour l'arrêt et la restauration des poids : la perte de validation."""
    return callbacks.EarlyStopping(monitor="val_loss", patience=patience, restore_best_weights=True, verbose=1)


# ============================================================================
# AUGMENTATION (train seulement, par construction)
# ============================================================================


def build_augmentation(
    flip: str | None = None,
    rotation: float = 0.05,
    zoom: float = 0.15,
    translation: float = 0.1,
    contrast: float = 0.2,
    brightness: float = 0.2,
    seed: int = RANDOM_SEED,
) -> tf.keras.Sequential:
    """Augmentations paramétrables : à choisir et justifier pour *ces* photos
    (cadrage approximatif, éclairage variable, texte sur l'emballage…)."""
    steps = []
    if flip:
        steps.append(layers.RandomFlip(flip, seed=seed))
    if rotation:
        steps.append(layers.RandomRotation(rotation, fill_mode="constant", seed=seed))
    if zoom:
        steps.append(layers.RandomZoom(zoom, fill_mode="constant", seed=seed))
    if translation:
        steps.append(layers.RandomTranslation(translation, translation, fill_mode="constant", seed=seed))
    if contrast:
        steps.append(layers.RandomContrast(contrast, seed=seed))
    if brightness:
        steps.append(layers.RandomBrightness(brightness, value_range=(0, 255), seed=seed))
    return tf.keras.Sequential(steps, name="augmentation")


# ============================================================================
# RÉFÉRENCE : CNN DE ZÉRO
# ============================================================================


def build_baseline_cnn(num_classes: int, image_size=(96, 96), learning_rate: float = 1e-3):
    """CNN simple : 3 blocs Conv-Conv-Pool, GlobalAveragePooling (au lieu de Flatten,
    pour ne pas exploser le nombre de paramètres de la tête), Dropout, Softmax."""
    h, w = image_size
    model = models.Sequential(
        [
            layers.Input(shape=(h, w, 3)),
            layers.Rescaling(1.0 / 255),
            *_conv_block(32),  # h → h/2
            *_conv_block(64),  # → h/4
            *_conv_block(128),  # → h/8
            layers.GlobalAveragePooling2D(),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.5),
            layers.Dense(num_classes, activation="softmax"),
        ],
        name="baseline_cnn",
    )
    return compile_model(model, learning_rate)


def _conv_block(filters: int):
    return [
        layers.Conv2D(filters, 3, padding="same", activation="relu"),
        layers.Conv2D(filters, 3, padding="same", activation="relu"),
        layers.MaxPooling2D(),
        layers.Dropout(0.25),
    ]


# ============================================================================
# TRANSFERT : MobileNetV2
# ============================================================================

BASE_PREFIX = "mobilenetv2"  # nom Keras : mobilenetv2_1.00_<taille>


def build_transfer_model(
    num_classes: int,
    image_size=(96, 96),
    augmentation: tf.keras.Sequential | None = None,
    dropout: float = 0.3,
    learning_rate: float = 1e-3,
):
    """MobileNetV2 ImageNet gelé + tête GAP-Dropout-Softmax (phase extraction de features).

    L'entrée passe par l'augmentation (éventuelle), puis par `preprocess_input`
    ([0, 255] → [-1, 1]), puis par la base appelée avec training=False : ses
    BatchNormalization restent en mode inférence, y compris pendant le fine-tuning."""
    h, w = image_size
    base = tf.keras.applications.MobileNetV2(input_shape=(h, w, 3), include_top=False, weights="imagenet")
    base.trainable = False

    inputs = tf.keras.Input(shape=(h, w, 3), name="image")
    x = augmentation(inputs) if augmentation is not None else inputs
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.Dropout(dropout, name="dropout")(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="predictions")(x)
    model = tf.keras.Model(inputs, outputs, name="mobilenetv2_transfer")
    return compile_model(model, learning_rate)


def get_base(model) -> tf.keras.Model:
    """Retrouve la base MobileNetV2 parmi les couches du modèle complet."""
    return next(layer for layer in model.layers if layer.name.startswith(BASE_PREFIX))


def unfreeze_top(model, n_layers: int, learning_rate: float = 1e-5):
    """Dégèle les `n_layers` dernières couches de la base (sauf les BatchNormalization)
    et recompile avec un learning rate faible. Renvoie le nombre de paramètres entraînables."""
    base = get_base(model)
    base.trainable = True
    for layer in base.layers[:-n_layers]:
        layer.trainable = False
    for layer in base.layers[-n_layers:]:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False
    compile_model(model, learning_rate)
    return count_trainable(model)


def count_trainable(model) -> int:
    return int(sum(tf.size(w).numpy() for w in model.trainable_weights))


# ============================================================================
# SAUVEGARDE
# ============================================================================


def save_bundle(model, metadata: dict, model_dir: os.PathLike = DEFAULT_MODEL_DIR) -> Path:
    """Écrit models/image_classifier/model.keras et metadata.json (lus par ImageClassifier.load)."""
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save(model_dir / MODEL_FILENAME)
    metadata = {
        "date": date.today().isoformat(),
        "seed": RANDOM_SEED,
        "credits": "Photos : contributeurs Open Food Facts (CC BY-SA)",
        **metadata,
    }
    (model_dir / METADATA_FILENAME).write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return model_dir
