"""
Évaluation du TP 17 : plancher, scores par rayon, matrice de confusion, seuil de
« je ne sais pas » et planche d'erreurs.

Rappel des règles : on compare et on choisit (modèle, seuil) sur la **validation** ;
le test n'est évalué qu'une fois, sur le modèle déjà choisi.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import accuracy_score, confusion_matrix

from .data import AISLE, CODE, LABEL, PATH, load_images


# ============================================================================
# PLANCHER ET SCORES
# ============================================================================


def floors(y_train, y_eval) -> dict:
    """Planchers à battre : hasard uniforme (1/K) et classe majoritaire du train."""
    y_train, y_eval = np.asarray(y_train), np.asarray(y_eval)
    k = len(np.unique(y_train))
    majority = np.bincount(y_train).argmax()
    return {"uniform": 1 / k, "majority": float(np.mean(y_eval == majority))}


def predict_proba(model, dataset) -> np.ndarray:
    return model.predict(dataset, verbose=0)


def per_aisle_accuracy(y_true, y_pred, aisles) -> pd.Series:
    """Accuracy par rayon (= rappel de chaque classe)."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    return pd.Series(
        {aisle: float(np.mean(y_pred[y_true == i] == i)) for i, aisle in enumerate(aisles)},
        name="accuracy",
    )


def plot_confusion(y_true, y_pred, aisles, title="", normalize=True, ax=None):
    """Matrice de confusion, normalisée par ligne (rayon réel) par défaut."""
    cm = confusion_matrix(y_true, y_pred, labels=range(len(aisles)), normalize="true" if normalize else None)
    ax = ax or plt.subplots(figsize=(7, 6))[1]
    sns.heatmap(cm, annot=True, fmt=".2f" if normalize else "d", cmap="Blues",
                xticklabels=aisles, yticklabels=aisles, ax=ax)
    ax.set(title=title, xlabel="Rayon prédit", ylabel="Rayon réel")
    return ax


def plot_history(history, title=""):
    """Courbes perte / accuracy, train et validation."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    epochs = range(1, len(history.history["loss"]) + 1)
    for ax, key in zip(axes, ("loss", "accuracy")):
        ax.plot(epochs, history.history[key], label="Train", linewidth=2)
        ax.plot(epochs, history.history[f"val_{key}"], "--", label="Validation", linewidth=2)
        ax.set(title=f"{title} — {key}", xlabel="Époque")
        ax.legend()
        ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


# ============================================================================
# SEUIL « JE NE SAIS PAS »
# ============================================================================


def coverage_curve(proba, y_true, thresholds=np.linspace(0, 0.99, 100)) -> pd.DataFrame:
    """Pour chaque seuil : part des photos auxquelles on répond (couverture) et
    accuracy sur ces seules photos."""
    proba, y_true = np.asarray(proba), np.asarray(y_true)
    confidence, y_pred = proba.max(axis=1), proba.argmax(axis=1)
    rows = []
    for t in thresholds:
        answered = confidence >= t
        acc = float(np.mean(y_pred[answered] == y_true[answered])) if answered.any() else np.nan
        rows.append({"threshold": float(t), "coverage": float(answered.mean()), "accuracy_answered": acc})
    return pd.DataFrame(rows)


def choose_threshold(curve: pd.DataFrame, min_accuracy: float) -> float:
    """Plus petit seuil dont l'accuracy sur les réponses atteint `min_accuracy`
    (donc la meilleure couverture pour cette exigence). À calculer sur la validation."""
    ok = curve[curve["accuracy_answered"] >= min_accuracy]
    if ok.empty:
        raise ValueError(f"aucun seuil n'atteint {min_accuracy:.0%} d'accuracy sur les réponses")
    return float(ok["threshold"].min())


def plot_coverage_curve(curve: pd.DataFrame, threshold: float | None = None, ax=None):
    ax = ax or plt.subplots(figsize=(7, 4))[1]
    ax.plot(curve["threshold"], curve["coverage"], label="Couverture (part répondue)")
    ax.plot(curve["threshold"], curve["accuracy_answered"], label="Accuracy sur les réponses")
    if threshold is not None:
        ax.axvline(threshold, color="gray", linestyle=":", label=f"Seuil = {threshold:.2f}")
    ax.set(xlabel="Seuil de confiance", ylim=(0, 1.02))
    ax.legend()
    ax.grid(alpha=0.3)
    return ax


# ============================================================================
# PLANCHE D'ERREURS
# ============================================================================


def errors_table(frame: pd.DataFrame, proba, aisles) -> pd.DataFrame:
    """Erreurs triées par confiance décroissante (les plus « sûres » d'abord).
    `frame` est la part évaluée, dans l'ordre du dataset (colonnes path, aisle, code, label)."""
    proba = np.asarray(proba)
    out = frame[[PATH, AISLE, CODE, LABEL]].copy()
    out["predicted"] = [aisles[i] for i in proba.argmax(axis=1)]
    out["confidence"] = proba.max(axis=1)
    out["proba_true"] = proba[np.arange(len(out)), out[LABEL].to_numpy()]
    return out[out["predicted"] != out[AISLE]].sort_values("confidence", ascending=False)


def plot_board(rows: pd.DataFrame, n_cols: int = 4, image_size=(200, 200), title=""):
    """Affiche des photos avec rayon réel, rayon prédit, confiance et code-barres."""
    n = len(rows)
    n_rows = max(1, int(np.ceil(n / n_cols)))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.2 * n_cols, 3.6 * n_rows), squeeze=False)
    images = load_images(rows[PATH].tolist(), image_size) if n else []
    for ax in axes.flat:
        ax.axis("off")
    for ax, img, (_, row) in zip(axes.flat, images, rows.iterrows()):
        ax.imshow(img)
        ax.set_title(f"réel : {row[AISLE]}\nprédit : {row['predicted']} ({row['confidence']:.0%})\n{row[CODE]}",
                     fontsize=9)
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_samples(frame: pd.DataFrame, n_per_aisle: int = 6, seed: int = 0, image_size=(160, 160)):
    """Planche aléatoire de photos par rayon (inspection du jeu)."""
    aisles = sorted(frame[AISLE].unique())
    fig, axes = plt.subplots(len(aisles), n_per_aisle, figsize=(2.2 * n_per_aisle, 2.4 * len(aisles)), squeeze=False)
    for i, aisle in enumerate(aisles):
        sample = frame[frame[AISLE] == aisle].sample(min(n_per_aisle, (frame[AISLE] == aisle).sum()), random_state=seed)
        for j, (img, code) in enumerate(zip(load_images(sample[PATH].tolist(), image_size), sample[CODE])):
            axes[i, j].imshow(img)
            axes[i, j].set_title(code, fontsize=7)
        for ax in axes[i]:
            ax.axis("off")
        axes[i, 0].set_title(aisle, fontsize=9, loc="left")
    fig.tight_layout()
    return fig


def summary_row(name: str, y_true, proba) -> dict:
    """Une ligne du tableau comparatif (sur la validation)."""
    return {"modèle": name, "accuracy": accuracy_score(y_true, np.asarray(proba).argmax(axis=1))}
