import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
import os

PNNS_1 = "pnns_groups_1"
NUTRIENTS = [
    "energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
    "sugars_100g", "fiber_100g", "proteins_100g", "salt_100g", "sodium_100g",
    "fruits-vegetables-legumes_100g",
]

def figure(fig, name: str):
    """Créer un dossier "figures" si non existant puis
    sauvegarde la figure en tant que "`name`.png" dans le dossier avant de l'afficher.
    """
    destination_dir = Path("./figures")
    if not destination_dir.is_dir():
        os.mkdir(destination_dir)
    fig.savefig(f"{destination_dir.as_posix()}/{name}.png", dpi=110)
    plt.show()
    
def d_cohen(a: pd.Series, b: pd.Series) -> float:
    std_pooled = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
    try:
        return (b.mean() - a.mean()) / std_pooled
    except ZeroDivisionError as e:
        print(e)
    return np.nan


def univariate_profile(s: pd.Series) -> pd.Series:
    x = s.dropna()
    q1, med, q3 = x.quantile([0.25, 0.5, 0.75])
    return pd.Series({
        "n": len(x), "manquants_pct": s.isna().mean() * 100, "moyenne": x.mean(), "mediane": med,
        "ecart_type": x.std(), "IQR": q3 - q1, "MAD": stats.median_abs_deviation(x),
        "CV": x.std() / x.mean(), "asymetrie": x.skew(), "aplatissement": x.kurt(),
        "p05": x.quantile(0.05), "p95": x.quantile(0.95), "min": x.min(), "max": x.max(),
    })

def profile_by_pnns_group(df, columns=NUTRIENTS, min_n=30):
    res = {}
    not_included_group = {}
    for r, g in df.groupby(PNNS_1, observed=True):
        s = g[columns].dropna(how="all")
        if len(s) < min_n:
            not_included_group[r] = len(s)
            continue
        
        # Création d'un DataFrame intermédiaire (index = nutriments, colonnes = stats)
        stat_df = pd.DataFrame({
            "mediane": s.median().round(2),
            "q25": s.quantile(0.25).round(2),
            "q75": s.quantile(0.75).round(2),
            "moyenne": s.mean().round(2),
            "n": s.notna().sum(),
        })
        
        # .stack() transforme ce tableau en une Série avec un MultiIndex (nutriment, stat)
        res[r] = stat_df.stack()

    not_included = pd.Series(not_included_group)

    if not res:
        return pd.DataFrame(), not_included
        
    # .T transpose pour avoir les rayons en index et les colonnes multi-niveaux
    return pd.DataFrame(res).T, not_included