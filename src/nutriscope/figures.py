"""
Tracés et sauvegarde des figures de l'analyse exploratoire (TP 10).

Le module ne calcule rien : il reçoit les tableaux produits par `eda.py`. Chaque fonction
`plot_*` renvoie une figure matplotlib ; `figure()` l'écrit en PNG puis l'affiche, ce qui
fonctionne avec le backend non interactif `Agg` (pas de `plt.show()`).

Les titres sont toujours passés en paramètre : c'est au notebook d'écrire le titre-message.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Résolu depuis l'emplacement du module : les PNG atterrissent au même endroit quel que
# soit le dossier depuis lequel le notebook ou nbconvert est lancé.
FIGURES_DIR = Path(__file__).resolve().parents[2] / "notebooks" / "figures"


def figure(fig: plt.Figure, name: str, directory: Path = FIGURES_DIR) -> Path:
    """Sauvegarde `fig` en `<directory>/<name>.png`, ferme la figure puis affiche le PNG écrit."""
    from IPython.display import Image, display

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    display(Image(filename=str(path)))
    return path


def plot_distributions(df: pd.DataFrame, columns: list[str], title: str, bins: int = 50) -> plt.Figure:
    """Un histogramme par colonne, avec la moyenne (tirets) et la médiane (trait plein)."""
    fig, axes = plt.subplots(1, len(columns), figsize=(5 * len(columns), 4), squeeze=False)
    for ax, column in zip(axes[0], columns):
        values = df[column].dropna()
        ax.hist(values, bins=bins, color="#8da0cb", edgecolor="white")
        ax.axvline(values.mean(), color="black", linestyle="--", label=f"moyenne {values.mean():.1f}")
        ax.axvline(values.median(), color="#d95f02", label=f"médiane {values.median():.1f}")
        ax.set_title(f"{column} (n = {len(values)})")
        ax.legend(fontsize=8)
    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


def plot_completeness(table: pd.DataFrame, title: str, xlabel: str,
                      column: str = "complete_pct") -> plt.Figure:
    """Barres du taux de fiches complètes par groupe, triées, avec l'effectif sous chaque nom."""
    data = table.sort_values(column)
    labels = [f"{name}\n(n = {n})" for name, n in zip(data.index, data["n"])]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, data[column], color="#55A868", edgecolor="black", linewidth=0.5)
    ax.axhline(100, color="black", linestyle="dotted")
    ax.set_ylim(0, 105)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Fiches complètes (%)")
    ax.tick_params(axis="x", labelrotation=45)
    plt.setp(ax.get_xticklabels(), ha="right")
    fig.tight_layout()
    return fig


def plot_correlations_by_group(table: pd.DataFrame, hue: str, title: str,
                               method: str = "spearman") -> plt.Figure:
    """Barres groupées : corrélation `method` de chaque nutriment avec la cible, une couleur par groupe."""
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(data=table, x="column", y=method, hue=hue, palette="tab10", ax=ax)
    ax.axhline(0, color="black", linewidth=1, linestyle="--")
    ax.set_title(title, fontsize=14, pad=15)
    ax.set_xlabel("Nutriment")
    ax.set_ylabel(f"Corrélation de {method.capitalize()}")
    ax.tick_params(axis="x", labelrotation=45)
    plt.setp(ax.get_xticklabels(), ha="right")
    ax.legend(title=hue, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    return fig
