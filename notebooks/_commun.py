import pandas as pd
import os

RAYON = "pnns_groups_1"
NUTRIMENTS = [
    "energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
    "sugars_100g", "fiber_100g", "proteins_100g", "salt_100g", "sodium_100g",
    "fruits-vegetables-legumes_100g",
]
NUTRIMENTS_CLES = [
    "energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
    "sugars_100g", "proteins_100g", "salt_100g",
]

def charger_propre(filepath: os.PathLike) -> tuple[pd.DataFrame, dict[str, int]]:
    """Échantillon nettoyé a minima + compte rendu des lignes écartées."""
    df = pd.read_csv(filepath, dtype={"code": "string"}, low_memory=False)
    cr = {"lignes_entree": len(df)}
    d = df.drop_duplicates(subset="code", keep="first")
    cr["doublons_codes"] = len(df) - len(d)
    ok = pd.Series(True, index=d.index)
    for c in NUTRIMENTS:
        if c != "energy-kcal_100g":
            ok &= d[c].isna() | d[c].between(0, 100)
    cr["hors_bornes"] = int((~ok).sum())
    d = d[ok]
    ok_e = d["energy-kcal_100g"].isna() | d["energy-kcal_100g"].between(0, 900)
    cr["energie_implausible"] = int((~ok_e).sum())
    d = d[ok_e]
    connu = d[RAYON].notna() & (d[RAYON] != "unknown")
    cr["rayon_inconnu"] = int((~connu).sum())
    d = d[connu].reset_index(drop=True)
    cr["lignes_sortie"] = len(d)
    return d, cr
