"""
Lecture de l'export Open Food Facts.

L'export complet (13 Go, environ 200 colonnes) ne tient pas en mémoire d'un bloc : le
parser C découpe toutes les colonnes d'une ligne avant d'appliquer `usecols`. On lit donc
par blocs : chaque bloc est découpé puis réduit aux colonnes utiles, et seuls ces blocs
réduits sont concaténés. Le code-barres est lu comme texte (sinon les zéros de tête sont
perdus).
"""

import os

import pandas as pd

TEXT_COLUMNS = {"code": str}
CHUNKSIZE = 100_000     # lignes par bloc : assez gros pour limiter le coût de la concaténation


def read_products(path: os.PathLike, columns: list[str] | None = None, sep: str = ",",
                  chunksize: int = CHUNKSIZE) -> pd.DataFrame:
    """
    Lit un export Open Food Facts (CSV, ou TSV avec `sep="\\t"` pour l'export complet).

    Seules les colonnes de `columns` présentes dans le fichier sont chargées ; les lignes
    mal formées sont signalées puis ignorées.
    """

    usecols = None
    if columns is not None:
        usecols = (lambda column: column in columns)
    chunks = pd.read_csv(
        path,
        sep=sep,
        usecols=usecols,
        dtype=TEXT_COLUMNS,
        on_bad_lines="warn",
        chunksize=chunksize,
    )
    return pd.concat(chunks, ignore_index=True)
