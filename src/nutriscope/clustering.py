"""
Bibliothèque de la segmentation du catalogue (TP 16, matinée).

Le notebook `notebooks/clustering.ipynb` raconte l'analyse ; ce module contient tout ce
qui doit pouvoir être testé et réutilisé, en particulier par le moteur de substitution
(`substitution.py`) qui devra mesurer les distances dans **le même espace** que K-Means.

Chaîne de préparation, dans cet ordre (chaque étape se chiffre dans le notebook) :

| Étape               | Objet                  | Pourquoi                                           |
| ------------------- | ---------------------- | -------------------------------------------------- |
| valeurs impossibles | `plausibility_flags()` | une erreur de saisie ne doit pas devenir un groupe |
| valeurs manquantes  | `GroupMedianImputer`   | médiane de la sous-catégorie, puis globale         |
| asymétrie           | `SkewedLog1p`          | `log1p` des colonnes à queue longue (skew > 1)     |
| normalisation       | `StandardScaler`       | chaque variable pèse pareil dans la distance       |

Les trois dernières étapes forment `make_preprocessor()`.

Le choix de k s'appuie sur `scan_k()` (inertie, silhouette, taille des groupes) et
`elbow_k()` (coude par distance à la corde) ; aucun score ne décide seul.

Données : © Open Food Facts contributors — ODbL.
"""

from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from .options import RANDOM_SEED
from .schema import (
    KCAL_MAX,
    KEY_NUTRIENTS,
    saturated_within_fat,
    sugars_within_carbohydrates,
)

# ============================================================================
# CONSTANTES
# ============================================================================

# Les 7 nutriments obligatoires (sans manquant) + les fibres (≈ 47 % de manquants)
FIBER = "fiber_100g"
CLUSTER_FEATURES = (*KEY_NUTRIENTS, FIBER)

GROUP_COL = "pnns_groups_2"          # niveau d'imputation : la sous-catégorie
AISLE_COL = "pnns_groups_1"          # rayon, utilisé par les règles métier
BEVERAGES = "Beverages"

SKEW_THRESHOLD = 1.0                 # au-delà, la colonne passe par log1p
K_RANGE = range(2, 11)               # k testés : de 2 à 10
SILHOUETTE_SAMPLE = 10_000           # la silhouette exacte est en O(n²)

# Règles de plausibilité propres au TP 16 (grammes pour 100 g) ; les autres viennent de `schema`
# Fibres exclues de la somme : aux États-Unis, les glucides affichés les incluent déjà ;
# les ajouter compterait les fibres deux fois et écarterait des céréales parfaitement réelles.
MASS_COLUMNS = ("fat_100g", "carbohydrates_100g", "proteins_100g", "salt_100g")
MASS_TOLERANCE_G = 2.0               # 4 valeurs arrondies à 0,5 g près : jusqu'à 2 g d'écart
MAX_BEVERAGE_SALT_G = 3.5            # une boisson n'est pas plus salée que l'eau de mer


# ============================================================================
# VALEURS IMPOSSIBLES
# ============================================================================

def plausibility_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Une colonne booléenne par règle de plausibilité ; `True` = produit à écarter.

    Les règles sont physiques (une masse ne dépasse pas 100 g pour 100 g, une partie ne
    dépasse pas le tout) ou métier (une boisson n'est pas plus salée que l'eau de mer).
    Un seuil global sur le sel serait faux : certains produits (nuoc-mâm, bouillons
    déshydratés) sont réellement très salés. Les valeurs manquantes ne déclenchent
    aucune règle.

    Les contrôles déjà définis au TP 9 (`schema.py`) sont réutilisés, pas recopiés : le
    jeu ML est censé les respecter, et un compteur non nul signalerait une régression.
    """
    mass_sum = df[list(MASS_COLUMNS)].fillna(0).sum(axis=1)
    return pd.DataFrame({
        "mass_over_100g": mass_sum > 100 + MASS_TOLERANCE_G,
        "energy_over_max": (df["energy-kcal_100g"] > KCAL_MAX).fillna(False),
        "saturated_over_fat": ~saturated_within_fat(df),
        "sugars_over_carbs": ~sugars_within_carbohydrates(df),
        "beverage_salt_over_seawater": ((df[AISLE_COL] == BEVERAGES)
                                        & (df["salt_100g"] > MAX_BEVERAGE_SALT_G)).fillna(False),
    }, index=df.index).astype(bool)


def implausible_mask(df: pd.DataFrame) -> pd.Series:
    """`True` pour les produits qui enfreignent au moins une règle de `plausibility_flags()`."""
    return plausibility_flags(df).any(axis=1)


# ============================================================================
# TRANSFORMATEURS
# ============================================================================

class GroupMedianImputer(BaseEstimator, TransformerMixin):
    """Impute les manquants par la médiane du groupe, puis par la médiane globale.

    Hypothèse : un produit dont la valeur est inconnue ressemble aux produits de sa
    sous-catégorie (une boisson à une boisson). La médiane globale ne sert qu'en dernier
    recours : groupe inconnu au `fit`, groupe manquant, ou groupe sans aucune valeur.

    Prend et renvoie un DataFrame complet : seules les colonnes `target_cols` changent,
    la colonne `group_col` reste disponible pour les étapes suivantes.
    """

    def __init__(self, target_cols: Sequence[str], group_col: str = GROUP_COL):
        self.target_cols = target_cols
        self.group_col = group_col

    def fit(self, X: pd.DataFrame, y=None):
        cols = list(self.target_cols)
        self.group_medians_ = X.groupby(self.group_col)[cols].median()
        self.global_medians_ = X[cols].median()
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "group_medians_")
        X_out = X.copy()
        for col in self.target_cols:
            missing = X_out[col].isna()
            if missing.any():
                by_group = X_out.loc[missing, self.group_col].map(self.group_medians_[col])
                X_out.loc[missing, col] = by_group.fillna(self.global_medians_[col])
        return X_out


class SkewedLog1p(BaseEstimator, TransformerMixin):
    """Applique `log1p` aux colonnes dont l'asymétrie (skewness) dépasse `threshold`.

    Les colonnes concernées sont choisies au `fit` (attribut `log_cols_`) puis figées :
    un nouveau produit, côté API, subira exactement la même transformation.
    `log1p` comprime les grandes valeurs sans changer l'ordre des produits et accepte
    les zéros ; il suppose des valeurs positives, ce que garantissent les règles de
    plausibilité et le nettoyage du TP 9.
    """

    def __init__(self, columns: Sequence[str], threshold: float = SKEW_THRESHOLD):
        self.columns = columns
        self.threshold = threshold

    def fit(self, X: pd.DataFrame, y=None):
        skewness = X[list(self.columns)].skew()
        self.skewness_ = skewness
        self.log_cols_ = [col for col in self.columns if skewness[col] > self.threshold]
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "log_cols_")
        X_out = X.copy()
        X_out[self.log_cols_] = np.log1p(X_out[self.log_cols_])
        return X_out


def make_preprocessor(features: Sequence[str] = CLUSTER_FEATURES,
                      group_col: str = GROUP_COL,
                      skew_threshold: float = SKEW_THRESHOLD) -> Pipeline:
    """Imputation par sous-catégorie → `log1p` des colonnes asymétriques → `StandardScaler`.

    Entrée : le DataFrame produits (au moins `features` et `group_col`).
    Sortie : une matrice numpy, une colonne par feature, dans l'ordre de `features`.
    Ce pipeline ajusté est l'objet à sauvegarder (joblib) pour l'API : sans lui, un
    nouveau produit ne serait pas projeté dans le même espace que le catalogue.
    """
    features = list(features)
    return Pipeline(steps=[
        ("impute", GroupMedianImputer(target_cols=features, group_col=group_col)),
        ("log", SkewedLog1p(columns=features, threshold=skew_threshold)),
        ("scale", ColumnTransformer(transformers=[("num", StandardScaler(), features)])),
    ])


# ============================================================================
# CHOIX DE k
# ============================================================================

def scan_k(X: np.ndarray, k_range: Iterable[int] = K_RANGE, seed: int = RANDOM_SEED,
           silhouette_sample: int = SILHOUETTE_SAMPLE) -> tuple[pd.DataFrame, dict[int, KMeans]]:
    """Ajuste un K-Means par k et renvoie (tableau des métriques indexé par k, modèles).

    Toutes les métriques sont calculées sur `X`, l'espace normalisé où K-Means a
    travaillé. Les tailles de groupes sont là pour démasquer une silhouette flatteuse :
    un score élevé avec un groupe de 5 produits signale des points isolés, pas une
    bonne segmentation.
    """
    rows, models = [], {}
    for k in k_range:
        model = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(X)
        sizes = np.bincount(model.labels_)
        models[k] = model
        rows.append({
            "k": k,
            "inertia": float(model.inertia_),
            "silhouette": float(silhouette_score(X, model.labels_,
                                                 sample_size=min(silhouette_sample, len(X)),
                                                 random_state=seed)),
            "davies_bouldin": float(davies_bouldin_score(X, model.labels_)),
            "calinski_harabasz": float(calinski_harabasz_score(X, model.labels_)),
            "min_cluster_size": int(sizes.min()),
            "max_cluster_pct": float(100 * sizes.max() / sizes.sum()),
        })
    scan = pd.DataFrame(rows).set_index("k")
    previous = scan["inertia"].shift(1)
    scan.insert(1, "inertia_gain_pct", 100 * (previous - scan["inertia"]) / previous)
    return scan, models


def elbow_k(ks: Iterable[int], inertia: Iterable[float]) -> int:
    """k du coude : le point le plus éloigné de la corde entre le premier et le dernier point.

    Les deux axes sont ramenés à [0, 1] (principe de la méthode « Kneedle ») ; pour une
    courbe décroissante et convexe, la distance à la corde vaut `1 - x - y`.
    L'axe des x est la liste **exacte** des k testés : un décalage d'un cran donnerait
    un coude faux d'une unité, sans aucune erreur.
    """
    ks = np.asarray(list(ks), dtype=float)
    y = np.asarray(list(inertia), dtype=float)
    if len(ks) != len(y) or len(ks) < 3:
        raise ValueError("Il faut au moins trois k, et autant d'inerties que de k.")
    x_norm = (ks - ks.min()) / (ks.max() - ks.min())
    y_norm = (y - y.min()) / (y.max() - y.min())
    return int(ks[np.argmax(1 - x_norm - y_norm)])


# ============================================================================
# INTERPRÉTATION
# ============================================================================

def cluster_deviations(df: pd.DataFrame, labels: Sequence[int],
                       features: Sequence[str] = CLUSTER_FEATURES) -> pd.DataFrame:
    """Écart de la moyenne de chaque groupe à la moyenne du catalogue, en écarts-types.

    Lecture : +1,5 en sucres = le groupe est nettement plus sucré que le catalogue.
    Calculé sur les valeurs observées (manquants ignorés), pas sur la matrice normalisée :
    on interprète des grammes réels, pas des log.
    """
    features = list(features)
    means = df[features].groupby(np.asarray(labels)).mean()
    return (means - df[features].mean()) / df[features].std()
