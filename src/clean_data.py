import pandas as pd

def read_products_data(columns=None):
    dtypes = {"code": "str"}
    chunks = pd.read_csv(
        "../data/en.openfoodfacts.org.products.csv",
        sep="\t",
        usecols=columns,
        iterator=True,
        chunksize=1000,
        on_bad_lines="warn",
        dtype=dtypes,
        # nrows=10000
    )

    return pd.concat(chunks, ignore_index=True)