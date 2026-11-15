"""
Jeu de photos du TP 17 : inventaire, exclusions, découpage et pipelines tf.data.

Règles tenues ici, et nulle part ailleurs :

- le découpage train / validation / test est stratifié par rayon, à graine fixe, et
  écrit sur disque (`split.csv`) : chaque photo garde son chemin, ce qui permet la
  planche d'erreurs ;
- le prétraitement (`load_image`) est le même à l'entraînement et dans l'application ;
- les images restent en [0, 255] : chaque modèle porte sa propre normalisation
  (Rescaling pour le CNN, preprocess_input pour MobileNetV2) ;
- aucune augmentation ici : elle vit dans le modèle (couches actives seulement
  à l'entraînement), donc elle ne peut pas toucher la validation ni le test.

Photos : CC BY-SA, contributeurs Open Food Facts.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split

from ..options import DATA_PATH, RANDOM_SEED, ROOT_PATH

IMAGES_PATH = DATA_PATH / "images"
SPLIT_FILE = IMAGES_PATH / "split.csv"
# Photos écartées après inspection (intrus : code-barres seul, tableau nutritionnel…)
EXCLUDED_FILE = ROOT_PATH / "src" / "images_bucket" / "excluded_images.csv"

IMAGE_SIZE = (96, 96)  # MobileNetV2 accepte 96, 128, 160, 192, 224
BATCH_SIZE = 32

PATH, AISLE, CODE, LABEL, SPLIT = "path", "aisle", "code", "label", "split"
TRAIN, VAL, TEST = "train", "val", "test"


# ============================================================================
# INVENTAIRE
# ============================================================================


def build_index(images_path: os.PathLike = IMAGES_PATH, aisles=None) -> pd.DataFrame:
    """Une ligne par photo : chemin, rayon (nom du dossier), code-barres (nom du fichier)."""
    images_path = Path(images_path)
    aisles = sorted(aisles) if aisles else sorted(p.name for p in images_path.iterdir() if p.is_dir())
    rows = [
        {PATH: str(path), AISLE: aisle, CODE: path.stem}
        for aisle in aisles
        for path in sorted((images_path / aisle).glob("*.jpg"))
    ]
    return pd.DataFrame(rows, columns=[PATH, AISLE, CODE])


def read_exclusions(excluded_file: os.PathLike = EXCLUDED_FILE) -> pd.DataFrame:
    """Liste des photos écartées (colonnes aisle, code, reason)."""
    if not Path(excluded_file).exists():
        return pd.DataFrame(columns=[AISLE, CODE, "reason"])
    return pd.read_csv(excluded_file, dtype=str, comment="#")


def apply_exclusions(index: pd.DataFrame, exclusions: pd.DataFrame) -> pd.DataFrame:
    """Retire les photos listées dans les exclusions (même rayon, même code)."""
    keys = set(zip(exclusions[AISLE], exclusions[CODE]))
    keep = [(a, c) not in keys for a, c in zip(index[AISLE], index[CODE])]
    return index[keep].reset_index(drop=True)


def check_readable(index: pd.DataFrame) -> pd.DataFrame:
    """Ouvre chaque photo ; renvoie celles que TensorFlow ne sait pas décoder."""
    unreadable = []
    for path in index[PATH]:
        try:
            tf.io.decode_image(tf.io.read_file(path), channels=3, expand_animations=False)
        except tf.errors.InvalidArgumentError:
            unreadable.append(path)
    return index[index[PATH].isin(unreadable)]


def image_sizes(index: pd.DataFrame) -> pd.DataFrame:
    """Hauteur / largeur d'origine de chaque photo (en-tête JPEG, sinon décodage)."""
    shapes = [_shape(p) for p in index[PATH]]
    return index.assign(height=[s[0] for s in shapes], width=[s[1] for s in shapes])


def _shape(path: str):
    raw = tf.io.read_file(path)
    try:
        return tf.io.extract_jpeg_shape(raw).numpy()
    except tf.errors.InvalidArgumentError:  # PNG ou WebP enregistré en .jpg
        return tf.shape(tf.io.decode_image(raw, channels=3, expand_animations=False)).numpy()


# ============================================================================
# DÉCOUPAGE
# ============================================================================


def make_split(index: pd.DataFrame, val_size=0.15, test_size=0.15, seed=RANDOM_SEED) -> pd.DataFrame:
    """Découpage stratifié par rayon en trois parts ; ajoute les colonnes split et label."""
    train_val, test = train_test_split(index, test_size=test_size, stratify=index[AISLE], random_state=seed)
    train, val = train_test_split(
        train_val, test_size=val_size / (1 - test_size), stratify=train_val[AISLE], random_state=seed
    )
    aisles = sorted(index[AISLE].unique())
    out = pd.concat([train.assign(**{SPLIT: TRAIN}), val.assign(**{SPLIT: VAL}), test.assign(**{SPLIT: TEST})])
    out[LABEL] = out[AISLE].map({a: i for i, a in enumerate(aisles)})
    return out.reset_index(drop=True)


def save_split(split: pd.DataFrame, path: os.PathLike = SPLIT_FILE) -> None:
    split.to_csv(path, index=False)


def load_split(path: os.PathLike = SPLIT_FILE) -> pd.DataFrame:
    return pd.read_csv(path, dtype={CODE: str})


def split_counts(split: pd.DataFrame) -> pd.DataFrame:
    """Effectifs rayon × part, avec totaux."""
    return pd.crosstab(split[AISLE], split[SPLIT], margins=True)[[TRAIN, VAL, TEST, "All"]]


# ============================================================================
# PIPELINES tf.data
# ============================================================================


def load_image(path, image_size=IMAGE_SIZE) -> tf.Tensor:
    """Lit une photo, 3 canaux, redimensionnée sans déformation (bandes noires), float32 en [0, 255]."""
    raw = tf.io.read_file(path)
    image = tf.io.decode_image(raw, channels=3, expand_animations=False)
    image = tf.image.resize_with_pad(image, image_size[0], image_size[1])
    return tf.cast(image, tf.float32)


def make_dataset(frame: pd.DataFrame, image_size=IMAGE_SIZE, batch_size=BATCH_SIZE, shuffle=False, seed=RANDOM_SEED):
    """Dataset (image, label) à partir des chemins. Mélange seulement si demandé (train)."""
    ds = tf.data.Dataset.from_tensor_slices((frame[PATH].to_numpy(), frame[LABEL].to_numpy()))
    if shuffle:
        ds = ds.shuffle(len(frame), seed=seed, reshuffle_each_iteration=True)
    ds = ds.map(lambda p, y: (load_image(p, image_size), y), num_parallel_calls=tf.data.AUTOTUNE)
    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def make_datasets(split: pd.DataFrame, image_size=IMAGE_SIZE, batch_size=BATCH_SIZE) -> dict:
    """Les trois datasets. L'ordre de val et test est celui de `split` (pour relier prédiction et photo)."""
    return {
        name: make_dataset(split[split[SPLIT] == name], image_size, batch_size, shuffle=(name == TRAIN))
        for name in (TRAIN, VAL, TEST)
    }


def load_images(paths, image_size=IMAGE_SIZE) -> np.ndarray:
    """Charge une petite liste de photos en mémoire (affichage, planches)."""
    return np.stack([load_image(p, image_size).numpy() for p in paths]).astype("uint8")
