"""
Accès en lecture seule au catalogue de produits, et fiche produit commune à tous les outils.

Deux implémentations de la même interface :

- ``PostgresCatalog`` : la base PostgreSQL de l'équipe (``schema_nutriscope.sql``), ouverte en
  lecture seule. C'est celle qu'utilisent l'assistant et le scanner ;
- ``InMemoryCatalog`` : une liste de lignes en mémoire, réservée aux tests unitaires et au
  développement hors ligne (jamais à la démonstration, qui se fait sur des données réelles).

Les deux rendent des lignes brutes (noms de colonnes de la base) ; ``build_fiche`` en fait la
fiche imposée par le contrat du TP 18. Une valeur inconnue vaut ``None``, jamais 0.

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

import math
import os
import re
from decimal import Decimal
from typing import Any, Iterable, Protocol

# ----------------------------------------------------------------------------
# Fiche produit
# ----------------------------------------------------------------------------

# Clé du contrat -> colonne de la base (table `nutrition`), valeurs pour 100 g
SHEET_NUTRIENTS = {
    "kcal": "energy_kcal_100g",
    "lipides": "fat_100g",
    "satures": "saturated_fat_100g",
    "sucres": "sugars_100g",
    "sel": "salt_100g",
    "fibres": "fiber_100g",
    "proteines": "proteins_100g",
}
# Valeurs en plus (hors contrat) : pour expliquer un score, et pour le scanner d'étiquettes
EXTRA_NUTRIENTS = {
    "kj": "energy_100g",
    "glucides": "carbohydrates_100g",
    "fruits_legumes_pct": "fruits_vegetables_legumes_100g",
}
GRADES = ("a", "b", "c", "d", "e")

DETAIL_COLUMNS = (
    "code", "name", "quantity", "pnns_group_1", "pnns_group_2", "brands", "labels",
    "nutriscore", "nutriscore_grade", "nova_group",
    *SHEET_NUTRIENTS.values(), *EXTRA_NUTRIENTS.values(),
)


def to_number(value: Any) -> float | None:
    """Valeur de la base -> float, ou None si inconnue (NULL, NaN, pas un nombre)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, (int, float)) and math.isfinite(value):
        return round(float(value), 3)
    return None


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(part) for part in value if part]


def build_fiche(row: dict[str, Any]) -> dict[str, Any]:
    """Ligne brute du catalogue -> fiche produit (contrat du TP 18, plus quelques clés en plus)."""
    nutrients = {key: to_number(row.get(column)) for key, column in SHEET_NUTRIENTS.items()}
    grade = row.get("nutriscore_grade")
    grade = grade.upper() if isinstance(grade, str) and grade.lower() in GRADES else None
    points = row.get("nutriscore")
    nova = row.get("nova_group")
    return {
        "code": str(row["code"]),
        "nom": row.get("name"),
        "marque": ", ".join(_split_list(row.get("brands"))) or None,
        "nutriscore": grade,
        "nutriments": nutrients,
        "donnees_incompletes": grade is None or any(v is None for v in nutrients.values()),
        # Clés en plus, permises par le contrat
        "score_nutriscore": int(points) if to_number(points) is not None else None,
        "nutriments_complementaires": {key: to_number(row.get(column)) for key, column in EXTRA_NUTRIENTS.items()},
        "rayon": row.get("pnns_group_1"),
        "categorie": row.get("pnns_group_2"),
        "quantite": row.get("quantity"),
        "nova": int(nova) if to_number(nova) is not None else None,
        "labels": _split_list(row.get("labels")),
    }


# ----------------------------------------------------------------------------
# Normalisation du texte (casse et accents ignorés), identique en Python et en SQL
# ----------------------------------------------------------------------------

_ACCENT_GROUPS = {"a": "àáâãäåā", "c": "çćč", "e": "èéêëēėę", "i": "ìíîïī", "n": "ñń", "o": "òóôõöøōœ",
                  "u": "ùúûüū", "y": "ýÿ", "z": "ž"}
_ACCENTED = "".join(_ACCENT_GROUPS.values())
_PLAIN = "".join(plain * len(accented) for plain, accented in _ACCENT_GROUPS.items())
_TRANSLATION = str.maketrans(_ACCENTED, _PLAIN)
_WORD = re.compile(r"[a-z0-9]+")
MAX_SEARCH_WORDS = 8


def normalize_text(text: str) -> str:
    """Minuscules, accents retirés (même correspondance que ``_sql_normalize``)."""
    return text.lower().translate(_TRANSLATION)


def search_words(text: str) -> list[str]:
    """Mots d'une recherche (lettres et chiffres seulement, donc sans danger dans un motif LIKE)."""
    return _WORD.findall(normalize_text(text))[:MAX_SEARCH_WORDS]


def _sql_normalize(expression: str) -> str:
    return f"translate(lower(coalesce({expression}, '')), '{_ACCENTED}', '{_PLAIN}')"


def code_variants(code: str) -> list[str]:
    """Un UPC-A à 12 chiffres est aussi stocké comme un EAN à 13 chiffres précédé d'un zéro, et inversement."""
    variants = [code]
    if len(code) == 12:
        variants.append("0" + code)
    elif len(code) == 13 and code.startswith("0"):
        variants.append(code[1:])
    return variants


# ----------------------------------------------------------------------------
# Interface du catalogue
# ----------------------------------------------------------------------------

class Catalog(Protocol):
    def find_by_code(self, code: str) -> list[dict[str, Any]]:
        """Lignes dont le code-barres est ``code`` (0 ou 1 en pratique)."""

    def search_by_name(self, words: list[str], limit: int) -> tuple[int, list[dict[str, Any]]]:
        """(nombre total de produits trouvés, ``limit`` meilleures lignes). Chaque mot doit figurer dans le nom ou la marque."""


def _rank_key(row: dict[str, Any], full: str) -> tuple:
    name = normalize_text(row.get("name") or "")
    grade = row.get("nutriscore_grade")
    return (name != full, not name.startswith(full), grade not in GRADES, len(name), str(row["code"]))


class InMemoryCatalog:
    """Catalogue en mémoire. Réservé aux tests unitaires et au développement hors ligne."""

    def __init__(self, rows: Iterable[dict[str, Any]]):
        self.rows = [dict(row) for row in rows]

    def find_by_code(self, code: str) -> list[dict[str, Any]]:
        variants = set(code_variants(code))
        return [row for row in self.rows if str(row["code"]) in variants]

    def search_by_name(self, words: list[str], limit: int) -> tuple[int, list[dict[str, Any]]]:
        def haystack(row):
            return normalize_text(f"{row.get('name') or ''} {row.get('brands') or ''}")

        matches = [row for row in self.rows if all(word in haystack(row) for word in words)]
        matches.sort(key=lambda row: _rank_key(row, " ".join(words)))
        return len(matches), matches[:limit]


class PostgresCatalog:
    """Le catalogue PostgreSQL de l'équipe, ouvert en lecture seule avec un délai maximal par requête."""

    _DETAILS = f"""
        SELECT p.code, p.name, p.quantity, p.pnns_group_1, p.pnns_group_2,
               (SELECT string_agg(b.name, ', ' ORDER BY b.name)
                  FROM products_brands pb JOIN brands b ON b.id = pb.brand_id
                 WHERE pb.product_code = p.code) AS brands,
               (SELECT string_agg(l.name, ', ' ORDER BY l.name)
                  FROM products_labels pl JOIN labels l ON l.id = pl.label_id
                 WHERE pl.product_code = p.code) AS labels,
               s.nutriscore, s.nutriscore_grade, s.nova_group,
               {", ".join("n." + column for column in (*SHEET_NUTRIENTS.values(), *EXTRA_NUTRIENTS.values()))}
          FROM products p
          LEFT JOIN nutrition n ON n.product_code = p.code
          LEFT JOIN score s ON s.product_code = p.code
    """

    def __init__(self, engine):
        self.engine = engine

    @classmethod
    def from_env(cls, statement_timeout_ms: int = 5000) -> "PostgresCatalog":
        """
        Paramètres de connexion du pipeline (``options.db_credentials`` : POSTGRES_USER / _HOST /
        _PORT du ``.env``, mot de passe dans POSTGRES_PASSWORD ou ``secrets/db_password.txt``).
        Nom de la base : NUTRISCOPE_DB, sinon ``[database] name`` d'``options.ini``.
        """
        from sqlalchemy import URL, create_engine

        from .options import CONFIG, db_credentials

        credentials = db_credentials()
        if credentials is None:
            raise RuntimeError("No PostgreSQL password: set POSTGRES_PASSWORD or create secrets/db_password.txt")
        url = URL.create(
            "postgresql+psycopg",
            username=credentials["username"],
            password=credentials["password"],
            host=credentials["host"],
            port=credentials["port"],
            database=os.getenv("NUTRISCOPE_DB") or CONFIG["database"]["name"],
        )
        # Session en lecture seule : quoi que demande le modèle, cette connexion ne peut rien écrire.
        options = f"-c default_transaction_read_only=on -c statement_timeout={int(statement_timeout_ms)}"
        engine = create_engine(url, pool_pre_ping=True, connect_args={"options": options, "connect_timeout": 5})
        return cls(engine)

    def _rows(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        from sqlalchemy import text

        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(text(sql), params)]

    def find_by_code(self, code: str) -> list[dict[str, Any]]:
        return self._rows(self._DETAILS + " WHERE p.code = ANY(:codes)", {"codes": code_variants(code)})

    def search_by_name(self, words: list[str], limit: int) -> tuple[int, list[dict[str, Any]]]:
        if not words:
            return 0, []
        name = _sql_normalize("p.name")
        brand = _sql_normalize("b.name")
        # Une condition par mot, sur un gabarit fixe : seuls les paramètres liés portent le texte de l'utilisateur.
        conditions = " AND ".join(
            f"({name} LIKE :w{i} OR EXISTS (SELECT 1 FROM products_brands pb JOIN brands b ON b.id = pb.brand_id "
            f"WHERE pb.product_code = p.code AND {brand} LIKE :w{i}))"
            for i in range(len(words))
        )
        sql = f"""
            WITH matches AS (
                SELECT p.code, count(*) OVER () AS total,
                       row_number() OVER (ORDER BY ({name} = :full) DESC, ({name} LIKE :prefix) DESC,
                                          coalesce(s.nutriscore_grade IN ('a', 'b', 'c', 'd', 'e'), false) DESC,
                                          length(p.name) NULLS LAST, p.code) AS rank
                  FROM products p LEFT JOIN score s ON s.product_code = p.code
                 WHERE {conditions}
            ), best AS (SELECT * FROM matches WHERE rank <= :limit)
            SELECT best.total, best.rank, details.*
              FROM best JOIN ({self._DETAILS}) AS details ON details.code = best.code
             ORDER BY best.rank
        """
        full = " ".join(words)
        params = {f"w{i}": f"%{word}%" for i, word in enumerate(words)}
        params.update(full=full, prefix=f"{full}%", limit=int(limit))
        rows = self._rows(sql, params)
        total = int(rows[0]["total"]) if rows else 0
        return total, rows


def default_catalog() -> Catalog:
    """Le catalogue utilisé par l'assistant et le scanner : PostgreSQL."""
    return PostgresCatalog.from_env()
