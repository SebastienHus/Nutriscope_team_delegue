"""
Moteur de substitution v1 (TP 16, après-midi) : « voici un produit comparable, mieux noté ».

Appelé par la future route `GET /produits/{code}/substituts` (TP 23) :

    engine = SubstitutionEngine().fit(catalog)      # une fois, au démarrage
    engine.suggest("3017620422003", n=3)            # à chaque requête

Pour un produit donné, `suggest()` applique dans l'ordre :

| Étape                 | Règle                                                             |
| --------------------- | ----------------------------------------------------------------- |
| garde produit         | code connu, Nutri-Score présent, données plausibles, pas d'alcool |
| même usage            | même sous-catégorie (`pnns_groups_2`) **et** même rayon           |
| mieux noté            | Nutri-Score strictement meilleur                                  |
| comparable            | distance ≤ `max_distance` dans l'espace de `make_preprocessor()`  |
| contraintes           | le substitut porte les labels alimentaires du produit (végan…)    |
| pas de doublon        | ni le produit lui-même, ni deux fois le même nom + marque         |
| classement            | labels de qualité partagés, puis Nutri-Score, puis distance       |

Deux familles de labels, deux rôles :
- **contraintes alimentaires** (`DIETARY_LABELS`) : filtre strict. Un produit sans gluten
  ne doit jamais être remplacé par un produit qui ne l'affirme pas ;
- **qualité ou engagement** (`QUALITY_LABELS`) : priorité de classement. Un substitut bio
  passe devant pour un produit bio, mais on propose quand même mieux sinon.
Les autres tags (emballage, origine, allégations, mentions Nutri-Score) sont ignorés.

La distance est mesurée dans le même espace que la segmentation du catalogue
(imputation, `log1p`, normalisation) : les deux briques restent cohérentes.
La colonne `labels_tags` est facultative : sans elle, les règles de labels sont inactives.

Données : © Open Food Facts contributors — ODbL.
"""

import unicodedata

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from .clustering import AISLE_COL, CLUSTER_FEATURES, GROUP_COL, implausible_mask, make_preprocessor

# ============================================================================
# CONSTANTES
# ============================================================================

CODE_COL = "code"
NAME_COL = "product_name"
BRANDS_COL = "brands"
GRADE_COL = "nutriscore_grade"
LABELS_COL = "labels_tags"

GRADES = ("a", "b", "c", "d", "e")
EXCLUDED_AISLES = ("Alcoholic beverages",)  # le Nutri-Score ne s'applique pas à l'alcool

# Rayon dans l'espace normalisé. Mesuré sur l'échantillon ML : distance médiane au plus
# proche voisin de la sous-catégorie 0,21 ; au plus proche candidat mieux noté 0,66.
# À 1,5, 82 % des produits ont au moins 3 suggestions (91 % à 2,0, mais le tri par
# Nutri-Score ferait alors remonter des produits nettement moins comparables).
MAX_DISTANCE = 1.5
DEFAULT_N = 3

# Labels → tags Open Food Facts qui les attestent (tags relevés dans l'échantillon ML)
DIETARY_LABELS = {
    "vegan": frozenset({"en:vegan", "en:european-vegetarian-union-vegan", "en:the-vegan-society",
                        "en:veganok"}),
    "vegetarian": frozenset({"en:vegetarian", "en:european-vegetarian-union",
                             "en:european-vegetarian-union-vegetarian"}),
    "gluten_free": frozenset({"en:no-gluten", "en:certified-gluten-free", "en:dzg-gluten-free"}),
    "lactose_free": frozenset({"en:no-lactose"}),
    "halal": frozenset({"en:halal", "fr:societe-francaise-de-controle-de-viande-halal"}),
    "kosher": frozenset({"en:kosher", "en:orthodox-union-kosher", "en:kosher-parve", "en:cor-kosher"}),
}
# Une contrainte peut être satisfaite par un label plus strict : végan ⇒ végétarien
SATISFIED_BY = {"vegetarian": ("vegan",)}

QUALITY_LABELS = {
    "organic": frozenset({"en:organic", "en:eu-organic", "fr:ab-agriculture-biologique",
                          "en:usda-organic"}),
    "fair_trade": frozenset({"en:fair-trade", "en:fairtrade-international", "en:fair-for-life",
                             "en:max-havelaar"}),
    "label_rouge": frozenset({"fr:label-rouge"}),
    "pdo": frozenset({"en:pdo", "fr:aoc", "fr:aop", "en:swiss-aoc"}),
    "pgi": frozenset({"en:pgi", "fr:igp", "en:swiss-pgi"}),
    "sustainable_fishing": frozenset({"en:sustainable-seafood-msc", "en:responsible-aquaculture-asc",
                                      "en:sustainable-fishery"}),
    "no_palm_oil": frozenset({"en:no-palm-oil"}),
    "rainforest_alliance": frozenset({"en:rainforest-alliance"}),
}
LABELS = {**DIETARY_LABELS, **QUALITY_LABELS}

REQUIRED_COLUMNS = (CODE_COL, NAME_COL, BRANDS_COL, GRADE_COL, AISLE_COL, GROUP_COL, *CLUSTER_FEATURES)
OUTPUT_COLUMNS = ("rank", CODE_COL, NAME_COL, BRANDS_COL, GRADE_COL, "distance",
                  "labels", "shared_labels")


# ============================================================================
# EXCEPTIONS
# ============================================================================

class ProductNotFoundError(KeyError):
    """Code-barres absent du catalogue (l'API répondra 404)."""


class NotSubstitutableError(ValueError):
    """Produit connu mais pour lequel aucune substitution n'a de sens (l'API répondra 422)."""


# ============================================================================
# OUTILS
# ============================================================================

def label_flags(labels_tags: pd.Series) -> pd.DataFrame:
    """Une colonne booléenne par label de `LABELS` : le produit porte-t-il l'un de ses tags ?

    `labels_tags` contient les tags Open Food Facts séparés par des virgules ; les
    valeurs manquantes donnent un produit sans label.
    """
    tags = labels_tags.fillna("").astype(str).str.split(",").map(lambda v: {t.strip() for t in v})
    return pd.DataFrame({name: tags.map(lambda found, wanted=wanted: not found.isdisjoint(wanted))
                         for name, wanted in LABELS.items()}, index=labels_tags.index).astype(bool)


def identity_key(names: pd.Series, brands: pd.Series) -> pd.Series:
    """Clé « même produit » : nom + marque, en minuscules, sans accents ni ponctuation.

    Les codes sont uniques après nettoyage, mais un même produit peut exister sous
    plusieurs codes (formats, multipacks, versions régionales). La clé sert à l'écarter.
    Elle n'est définie que si le nom **et** la marque sont connus : sans marque, un nom
    générique (« Pain complet », « Comté ») désigne des produits différents, de
    Nutri-Scores différents, qu'il ne faut surtout pas fusionner. Clé vide = jamais doublon.
    """
    def normalize(text) -> str:
        if pd.isna(text):
            return ""
        ascii_text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
        return " ".join("".join(ch if ch.isalnum() else " " for ch in ascii_text.lower()).split())

    name = names.map(normalize)
    brand = brands.map(normalize)
    return (name + "|" + brand).where((name != "") & (brand != ""), "")


# ============================================================================
# MOTEUR
# ============================================================================

class SubstitutionEngine(BaseEstimator):
    """Moteur de substitution : `fit()` une fois sur le catalogue, puis `suggest()` par produit.

    Attributs après `fit()` :
    - `catalog_` : produits retenus, indexés par position (même ordre que `X_`) ;
    - `labels_` : une colonne booléenne par label de `LABELS`, même ordre que `catalog_` ;
    - `X_` : matrice normalisée des nutriments (espace de `make_preprocessor()`) ;
    - `rejected_codes_` : codes écartés pour données incohérentes ;
    - `labels_available_` : les règles de labels sont-elles actives (`labels_tags` fournie) ?
    """

    def __init__(self, max_distance: float = MAX_DISTANCE, preprocessor: Pipeline | None = None):
        self.max_distance = max_distance
        self.preprocessor = preprocessor

    # ------------------------------------------------------------------ fit

    def fit(self, catalog: pd.DataFrame) -> "SubstitutionEngine":
        missing = [column for column in REQUIRED_COLUMNS if column not in catalog.columns]
        if missing:
            raise ValueError(f"Missing columns in the catalog: {missing}")
        if catalog[CODE_COL].duplicated().any():
            raise ValueError("Duplicated product codes in the catalog")

        implausible = implausible_mask(catalog)
        self.rejected_codes_ = frozenset(catalog.loc[implausible, CODE_COL].astype(str))
        kept = catalog.loc[~implausible].reset_index(drop=True)

        self.preprocessor_ = clone(self.preprocessor or make_preprocessor()).fit(kept)
        self.X_ = self.preprocessor_.transform(kept)

        self.labels_available_ = LABELS_COL in kept.columns
        labels_tags = kept[LABELS_COL] if self.labels_available_ else pd.Series(None, index=kept.index)
        self.labels_ = label_flags(labels_tags)

        grades = kept[GRADE_COL].astype("string").str.lower()
        self.catalog_ = pd.DataFrame({
            CODE_COL: kept[CODE_COL].astype(str),
            NAME_COL: kept[NAME_COL],
            BRANDS_COL: kept[BRANDS_COL],
            GRADE_COL: grades,
            "grade_rank": grades.map({grade: i for i, grade in enumerate(GRADES)}),
            AISLE_COL: kept[AISLE_COL],
            GROUP_COL: kept[GROUP_COL],
            "identity": identity_key(kept[NAME_COL], kept[BRANDS_COL]),
            "labels": self.labels_.apply(lambda flags: ", ".join(flags.index[flags]), axis=1),
        })
        self.position_ = pd.Series(np.arange(len(kept)), index=self.catalog_[CODE_COL])
        self.groups_ = {group: np.asarray(positions)
                        for group, positions in self.catalog_.groupby(GROUP_COL).indices.items()}
        return self

    # -------------------------------------------------------------- suggest

    def suggest(self, code: str, n: int = DEFAULT_N) -> pd.DataFrame:
        """Jusqu'à `n` substituts pour `code`, du meilleur au moins bon (colonnes `OUTPUT_COLUMNS`).

        `labels` liste les labels reconnus du substitut ; `shared_labels` compte les labels
        de qualité qu'il partage avec le produit scanné (de quoi expliquer la suggestion).
        Un résultat vide n'est pas une erreur : produit déjà classé A, ou aucun produit
        mieux noté, assez proche et compatible. Lève `ProductNotFoundError` ou
        `NotSubstitutableError` quand la question elle-même n'a pas de réponse.
        """
        check_is_fitted(self, "catalog_")
        if n < 1:
            raise ValueError("n must be at least 1")
        position = self._product_position(str(code))
        product = self.catalog_.iloc[position]
        product_labels = self.labels_.iloc[position]

        candidates = self.groups_.get(product[GROUP_COL], np.array([], dtype=int))
        table = self.catalog_.iloc[candidates]
        keep = (
            (table[AISLE_COL] == product[AISLE_COL]).fillna(False).to_numpy(dtype=bool)
            & (table["grade_rank"] < product["grade_rank"]).fillna(False).to_numpy(dtype=bool)
            & (candidates != position)
            & self._meets_dietary_constraints(candidates, product_labels)
        )
        if product["identity"]:
            keep &= (table["identity"] != product["identity"]).to_numpy()
        candidates = candidates[keep]

        distances = np.linalg.norm(self.X_[candidates] - self.X_[position], axis=1)
        close = distances <= self.max_distance
        candidates, distances = candidates[close], distances[close]

        wanted_quality = [name for name in QUALITY_LABELS if product_labels[name]]
        shared = self.labels_.iloc[candidates][wanted_quality].sum(axis=1).to_numpy(dtype=int)
        result = self.catalog_.iloc[candidates].assign(distance=distances, shared_labels=shared)

        # Labels de qualité partagés d'abord, puis Nutri-Score, puis proximité
        result = result.sort_values(["shared_labels", "grade_rank", "distance"],
                                    ascending=[False, True, True], kind="stable")
        result = result[(result["identity"] == "") | ~result["identity"].duplicated()]

        result = result.head(n).reset_index(drop=True)
        result.insert(0, "rank", np.arange(1, len(result) + 1))
        return result[list(OUTPUT_COLUMNS)]

    def _meets_dietary_constraints(self, candidates: np.ndarray, product_labels: pd.Series) -> np.ndarray:
        """Masque des candidats qui portent toutes les contraintes alimentaires du produit."""
        ok = np.ones(len(candidates), dtype=bool)
        flags = self.labels_.iloc[candidates]
        for name in DIETARY_LABELS:
            if product_labels[name]:
                accepted = [name, *SATISFIED_BY.get(name, ())]
                ok &= flags[accepted].any(axis=1).to_numpy()
        return ok

    def _product_position(self, code: str) -> int:
        if code in self.rejected_codes_:
            raise NotSubstitutableError(f"{code}: inconsistent nutrition data, no substitution")
        if code not in self.position_.index:
            raise ProductNotFoundError(code)
        position = int(self.position_[code])
        product = self.catalog_.iloc[position]
        if product[AISLE_COL] in EXCLUDED_AISLES:
            raise NotSubstitutableError(f"{code}: no Nutri-Score substitution for {product[AISLE_COL]}")
        if pd.isna(product["grade_rank"]):
            raise NotSubstitutableError(f"{code}: no Nutri-Score grade")
        if pd.isna(product[GROUP_COL]):
            raise NotSubstitutableError(f"{code}: unknown sub-category")
        return position
