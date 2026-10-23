"""
Fonctions de calcul de l'analyse exploratoire de référence (TP 10).

Aucune fonction de ce module n'affiche ni ne trace : chacune prend des données et renvoie
un tableau (DataFrame, Series ou dict). Les figures vivent dans `figures.py`, la narration
dans `notebooks/eda_reference.ipynb`, et chaque fonction est testée dans `tests/test_eda.py`.

Conventions :
- statistiques robustes par défaut (médiane, quartiles, MAD) ; la moyenne n'est donnée
  qu'accompagnée de l'écart-type ;
- chaque tableau porte ses effectifs (`n`) ;
- les groupes trop petits sont écartés et listés, jamais complétés en baissant le seuil ;
- les fonctions ne modifient jamais le DataFrame reçu.
"""

import numpy as np
import pandas as pd
from scipy import stats

from . import schema

# ============================================================================
# CONSTANTES
# ============================================================================

PNNS_1 = "pnns_groups_1"
PNNS_2 = "pnns_groups_2"
SCORE = "nutriscore_score"
GRADE = "nutriscore_grade"
UNKNOWN = "unknown"
GRADES = ("a", "b", "c", "d", "e")

# Nutriments étudiés : les nutriments clés du schéma, plus fibres et sodium. Le sodium est
# gardé pour pouvoir constater sa redondance avec le sel (sel = sodium × 2,5).
NUTRIENTS = [
    "energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
    "sugars_100g", "fiber_100g", "proteins_100g", "salt_100g", "sodium_100g",
]

# Facteurs qui rendent un écart absolu comparable à un écart-type sous hypothèse normale
MAD_TO_STD = 1.4826         # médiane des écarts absolus
MEAN_AD_TO_STD = 1.2533     # moyenne des écarts absolus (repli quand la MAD vaut 0)


# ============================================================================
# PÉRIMÈTRE
# ============================================================================

def exclude_unknown(df: pd.DataFrame, group: str = PNNS_1) -> pd.DataFrame:
    """Retire les lignes dont le groupe est manquant ou vaut `unknown` (comparaisons par rayon)."""
    return df[df[group].notna() & (df[group] != UNKNOWN)]


# ============================================================================
# 1. DISTRIBUTIONS
# ============================================================================

def univariate_profile(s: pd.Series) -> pd.Series:
    """
    Résumé univarié d'une variable numérique : effectif, part de manquants, tendance
    centrale, dispersion (écart-type, IQR, MAD), forme (asymétrie, aplatissement) et quantiles.
    Le coefficient de variation vaut NaN quand la moyenne est nulle.
    """
    x = s.dropna()
    q05, q1, med, q3, q95 = (x.quantile([0.05, 0.25, 0.5, 0.75, 0.95]).tolist()
                            if len(x) else [np.nan] * 5)
    mean, std = x.mean(), x.std()
    return pd.Series({
        "n": len(x),
        "missing_pct": s.isna().mean() * 100 if len(s) else np.nan,
        "mean": mean,
        "median": med,
        "std": std,
        "iqr": q3 - q1,
        "mad": stats.median_abs_deviation(x) if len(x) else np.nan,
        "cv": std / mean if mean else np.nan,
        "skewness": x.skew(),
        "kurtosis": x.kurt(),
        "p05": q05, "q25": q1, "q75": q3, "p95": q95,
        "min": x.min(), "max": x.max(),
    }, name=s.name)


def profile_by_group(df: pd.DataFrame, columns: list[str] = NUTRIENTS, group: str = PNNS_1,
                     min_n: int = 30) -> tuple[pd.DataFrame, pd.Series]:
    """
    Médiane, quartiles, moyenne et effectif de chaque nutriment, par groupe.

    Les groupes de moins de `min_n` produits sont écartés. Retourne le tableau (une ligne
    par groupe, colonnes à deux niveaux `(nutriment, statistique)`) et la Series des groupes
    écartés avec leur effectif.
    """
    sizes = df.groupby(group, observed=True).size()
    excluded = sizes[sizes < min_n].sort_values()
    kept = df[df[group].isin(sizes[sizes >= min_n].index)]

    grouped = kept.groupby(group, observed=True)[columns]
    table = pd.concat({
        "median": grouped.median(),
        "q25": grouped.quantile(0.25),
        "q75": grouped.quantile(0.75),
        "mean": grouped.mean(),
        "n": grouped.count(),
    }, axis=1)
    order = pd.MultiIndex.from_product([columns, ["median", "q25", "q75", "mean", "n"]])
    table = table.swaplevel(axis=1).reindex(columns=order)
    return table, excluded


def grade_crosstab(df: pd.DataFrame, group: str = PNNS_1) -> pd.DataFrame:
    """
    Effectifs croisés groupe × grade Nutri-Score, limités aux grades a à e (les valeurs
    `unknown` ou `not-applicable` créeraient des lignes vides qui faussent le V de Cramér).
    """
    graded = df[df[GRADE].isin(GRADES)]
    counts = pd.crosstab(graded[group], graded[GRADE])
    return counts.reindex(columns=list(GRADES), fill_value=0)


def cramers_v(counts: pd.DataFrame) -> float:
    """
    V de Cramér d'un tableau de contingence **en effectifs** (jamais en pourcentages :
    le khi-deux dépend de l'effectif total). Vaut 0 sans association, 1 si la ligne
    détermine la colonne. NaN si le tableau a moins de deux lignes ou deux colonnes non vides.
    """
    table = counts.loc[counts.sum(axis=1) > 0, counts.sum(axis=0) > 0]
    k = min(table.shape) - 1
    if k < 1:
        return np.nan
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    return float(np.sqrt(chi2 / (table.to_numpy().sum() * k)))


# ============================================================================
# 2. COMPLÉTUDE ET QUALITÉ
# ============================================================================

def main_brand(brands: pd.Series) -> pd.Series:
    """Première marque d'un champ `brands` multi-valué (« Carrefour, Carrefour Bio » → « Carrefour »)."""
    return brands.str.split(",").str[0].str.strip().replace("", np.nan)


def completeness_by_group(df: pd.DataFrame, group: str, columns: list[str] = schema.KEY_NUTRIENTS,
                          score_column: str = GRADE, min_n: int = 20) -> pd.DataFrame:
    """
    Taux de présence (en %) de chaque colonne de `columns`, taux de fiches complètes
    (toutes les colonnes présentes) et taux de présence du score, par groupe.

    Seuls les groupes d'au moins `min_n` produits sont gardés ; le tableau est trié par
    effectif décroissant et porte la colonne `n`.
    """
    present = [column for column in columns if column in df.columns]
    if not present:
        raise ValueError("Aucune des colonnes demandées n'est présente dans la table.")

    flags = df[present].notna()
    flags["complete_pct"] = flags.all(axis=1)
    if score_column in df.columns:
        flags["score_pct"] = df[score_column].notna()
    flags[group] = df[group]

    grouped = flags.groupby(group, observed=True)
    table = (grouped.mean() * 100).round(1)
    table.insert(0, "n", grouped.size())
    return table[table["n"] >= min_n].sort_values("n", ascending=False)


def business_inconsistencies(df: pd.DataFrame, energy_gap_kcal: float = 150.0) -> pd.DataFrame:
    """
    Drapeaux booléens d'incohérence métier, un par produit (on compte, on ne corrige pas) :

    - `sugars_over_carbohydrates` : sucres > glucides (tolérance d'arrondi du schéma, 0,5 g) ;
    - `saturated_over_fat` : saturés > lipides (même tolérance) ;
    - `salt_sodium_mismatch` : |sel − 2,5 × sodium| > 0,1 g ;
    - `energy_gap` : énergie déclarée à plus de `energy_gap_kcal` de l'énergie calculée 4 / 4 / 9 ;
    - `zero_energy_with_macros` : énergie déclarée nulle alors que des macronutriments sont présents.

    Les trois premières règles réutilisent celles de `schema.py`, pour que l'EDA et le
    nettoyage parlent des mêmes incohérences. Une valeur manquante ne lève jamais de drapeau.
    """
    declared = df["energy-kcal_100g"]
    computed = schema.compute_energy_kcal(df)
    macros = df[list(schema.KCAL_PER_GRAM)].fillna(0).sum(axis=1)
    return pd.DataFrame({
        "sugars_over_carbohydrates": ~schema.sugars_within_carbohydrates(df),
        "saturated_over_fat": ~schema.saturated_within_fat(df),
        "salt_sodium_mismatch": ~schema.salt_matches_sodium(df),
        "energy_gap": ((declared - computed).abs() > energy_gap_kcal).fillna(False),
        "zero_energy_with_macros": ((declared == 0) & (macros > 0)).fillna(False),
    }, index=df.index).astype(bool)


# ============================================================================
# 3. CORRÉLATIONS
# ============================================================================

CORRELATION_COLUMNS = ["n", "pearson", "spearman"]


def correlations_with_target(df: pd.DataFrame, columns: list[str], target: str,
                             min_n: int = 30) -> pd.DataFrame:
    """
    Pearson et Spearman de chaque colonne avec `target`, sur les paires complètes.

    Les colonnes de moins de `min_n` paires sont omises. Le tableau est trié par |Spearman|
    décroissant (le signe est conservé) ; il est vide mais bien formé si rien n'est calculable.
    """
    rows = {}
    for column in columns:
        pairs = df[[column, target]].dropna()
        if len(pairs) < min_n:
            continue
        rows[column] = {
            "n": len(pairs),
            "pearson": pairs[column].corr(pairs[target]),
            "spearman": pairs[column].corr(pairs[target], method="spearman"),
        }
    # Types forcés : un tableau vide serait sinon de type `object` et contaminerait un `concat`
    table = (pd.DataFrame.from_dict(rows, orient="index", columns=CORRELATION_COLUMNS)
             .astype({"n": int, "pearson": float, "spearman": float}))
    return table.sort_values("spearman", key=abs, ascending=False)


def correlations_by_group(df: pd.DataFrame, columns: list[str], target: str,
                          group: str = PNNS_1, min_n: int = 30) -> pd.DataFrame:
    """
    `correlations_with_target` dans chaque groupe, en format long
    (`group`, `column`, `n`, `pearson`, `spearman`). Un couple groupe × colonne de moins
    de `min_n` paires est absent : c'est voulu, on ne baisse pas le seuil.
    """
    parts = []
    for name, part in df.groupby(group, observed=True):
        table = correlations_with_target(part, columns, target, min_n)
        parts.append(table.rename_axis("column").reset_index().assign(**{group: name}))
    if not parts:
        return pd.DataFrame(columns=[group, "column", *CORRELATION_COLUMNS])
    return pd.concat(parts, ignore_index=True)[[group, "column", *CORRELATION_COLUMNS]]


def redundant_pairs(matrix: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
    """
    Paires de variables dont la corrélation vaut au moins `threshold` en valeur absolue,
    lues dans le triangle supérieur d'une matrice de corrélation, triées par |rho| décroissant.
    """
    columns = list(matrix.columns)
    rows = [
        {"var_1": a, "var_2": b, "rho": matrix.loc[a, b]}
        for i, a in enumerate(columns)
        for b in columns[i + 1:]
        if abs(matrix.loc[a, b]) >= threshold
    ]
    pairs = pd.DataFrame(rows, columns=["var_1", "var_2", "rho"])
    return pairs.sort_values("rho", key=abs, ascending=False, ignore_index=True)


# ============================================================================
# 4. VALEURS EXTRÊMES
# ============================================================================

def robust_zscore(s: pd.Series) -> pd.Series:
    """
    Z-score robuste : (x − médiane) / (MAD × 1,4826).

    Quand plus de la moitié des valeurs sont identiques (typiquement 0 g de lipides dans
    les boissons), la MAD vaut 0 et la division donnerait l'infini pour toute valeur non
    nulle. On se replie alors sur la moyenne des écarts absolus × 1,2533 ; si elle vaut
    aussi 0 (série constante), le score est NaN : aucune valeur n'est extrême.
    """
    x = s.dropna()
    if x.empty:
        return pd.Series(np.nan, index=s.index, dtype=float)
    median = x.median()
    scale = stats.median_abs_deviation(x, scale="normal")
    if not scale:
        scale = (x - median).abs().mean() * MEAN_AD_TO_STD
    if not scale:
        return pd.Series(np.nan, index=s.index, dtype=float)
    return (s - median) / scale


EXTREME_COLUMNS = ["nutrient", "value", "group_median", "z"]


def remaining_extremes(df: pd.DataFrame, columns: list[str] = NUTRIENTS, group: str = PNNS_1,
                       threshold: float = 3.5,
                       id_columns: tuple[str, ...] = ("code", "product_name")) -> pd.DataFrame:
    """
    Valeurs à plus de `threshold` z-scores robustes de la médiane **de leur groupe**, dans
    les deux sens, en format long (une ligne par produit × nutriment), triées par |z|
    décroissant. L'index d'origine du produit est conservé.
    """
    ids = [column for column in (*id_columns, group) if column in df.columns]
    parts = []
    for column in columns:
        grouped = df.groupby(group, observed=True)[column]
        z = grouped.transform(robust_zscore)
        flagged = z.abs() > threshold
        if flagged.any():
            parts.append(df.loc[flagged, ids].assign(
                nutrient=column,
                value=df.loc[flagged, column],
                group_median=grouped.transform("median")[flagged],
                z=z[flagged],
            ))
    if not parts:
        return pd.DataFrame(columns=[*ids, *EXTREME_COLUMNS])
    return pd.concat(parts).sort_values("z", key=abs, ascending=False)


# ============================================================================
# 5. HYPOTHÈSES
# ============================================================================

def cohens_d(a: pd.Series, b: pd.Series) -> float:
    """
    d de Cohen de `b` par rapport à `a` (positif si `b` est plus grand), avec l'écart-type
    combiné. NaN si un groupe a moins de deux valeurs ou si la dispersion est nulle.
    """
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return np.nan
    pooled = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
    if not pooled:
        return np.nan
    return float((b.mean() - a.mean()) / pooled)


def compare_two_groups(a: pd.Series, b: pd.Series) -> dict:
    """
    Comparaison exploratoire de deux échantillons : effectifs, médianes, écart des médianes
    (b − a), d de Cohen et p-valeur du test de Mann-Whitney bilatéral.
    """
    a, b = a.dropna(), b.dropna()
    p_value = (stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
               if len(a) and len(b) else np.nan)
    return {
        "n_a": len(a), "n_b": len(b),
        "median_a": a.median(), "median_b": b.median(),
        "median_diff": b.median() - a.median(),
        "cohens_d": cohens_d(a, b),
        "p_value": float(p_value),
    }


def compare_by_group(df: pd.DataFrame, value: str, label_column: str, label_a, label_b,
                     group: str = PNNS_1, min_n: int = 10) -> pd.DataFrame:
    """
    `compare_two_groups` stratifié : dans chaque groupe, compare `value` entre les lignes
    où `label_column` vaut `label_a` et celles où il vaut `label_b`. Les groupes où l'un
    des deux côtés a moins de `min_n` valeurs sont omis.
    """
    rows = {}
    for name, part in df.groupby(group, observed=True):
        a = part.loc[part[label_column] == label_a, value].dropna()
        b = part.loc[part[label_column] == label_b, value].dropna()
        if len(a) >= min_n and len(b) >= min_n:
            rows[name] = compare_two_groups(a, b)
    table = pd.DataFrame.from_dict(rows, orient="index",
                                   columns=["n_a", "n_b", "median_a", "median_b",
                                            "median_diff", "cohens_d", "p_value"])
    return table.rename_axis(group)
