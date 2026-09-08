import argparse
import os
import sqlparse
import configparser
import pandas as pd
from sqlalchemy import create_engine, URL
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.schema import CreateTable

from clean_data import read_products_data, clean_products_data

def read_database_options(filename):
    config_obj = configparser.ConfigParser(allow_no_value=True) # Requis pour autoriser les listes sans valeur
    config_obj.read(filename)

    # convert to dict
    config = {s:dict(config_obj.items(s)) for s in config_obj.sections()}
    config["database"]["categories"] = [category.strip() for category in config["database"]["categories"].split(",")]

    return config

def init_database(config, username, password):
    url = URL.create(
        "postgresql+psycopg",
        username=username,
        password=password,
        host="localhost",
        port=5432,
        database=config["database"]["name"],
    )

    engine = create_engine(url, echo=True)
    if not database_exists(engine.url):
        create_database(engine.url)

    # 1. Lecture du fichier SQL
    with open("./schema_nutriscope.sql", "r", encoding="utf-8") as file:
        sql_script = file.read()

    statements = sqlparse.split(sql_script)

    # 2. Exécution avec gestion de la transaction
    with engine.begin() as conn:
        # engine.begin() ouvre une transaction et fait automatiquement un COMMIT à la fin du bloc
        
        # Récupération de la connexion brute psycopg3
        raw_conn = conn.connection

        # Pour exécuter plusieurs instructions séparées par des ';' selon le pilote
        # On utilise la connexion DBAPI sous-jacente si execute() échoue sur le script complet
        # Exécution du script via le curseur PostgreSQL natif
        with raw_conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
            
                # On vérifie si la commande a renvoyé des résultats
                if cursor.description is not None:
                    resultats = cursor.fetchall()
                    for ligne in resultats:
                        print(ligne)
                elif cursor.statusmessage is not None:
                    # cursor.statusmessage contient la réponse du serveur (ex: "DROP TABLE", "UPDATE 5")
                    print(f"Commande exécutée avec succès : {cursor.statusmessage}")
        print("Script exécuté avec succès.")

    return engine

# def save_db_file(engine, filename):
#     with open(filename, "w") as file:
#         file.write(CreateTable(my_mysql_table).compile(mysql_engine))

def to_list(value):
    if not isinstance(value, str):
        return []
    return [v.strip() for v in value.split(",")]

def get_multi_relationship(
        data_frame: pd.DataFrame,
        column_to_split: str,
        primary_keys: tuple[str],
        split= to_list,
        as_:dict = None
    ):
    as_ = as_ or {}
    _from_id, to_id = primary_keys
    from_id = as_.get(_from_id, _from_id)

    # 1. Copie et application de la fonction de découpage
    df = data_frame.copy()
    df["_temp_tags"] = df[column_to_split].apply(split)

    # 2. Éclatement (explode) pour avoir une ligne par élément
    exploded = df.explode("_temp_tags").dropna(subset=["_temp_tags"])

    # 3. Création de la table de référence unique (right_table)
    unique_tags = exploded["_temp_tags"].drop_duplicates().reset_index(drop=True)
    right_table = pd.DataFrame({"id": unique_tags.index, "name": unique_tags})

    # 4. Association des IDs de la table de référence vers la table de relation
    tag_to_id = {name: idx for idx, name in unique_tags.items()}
    
    relation_data = []
    for _, row in exploded.iterrows():
        relation_data.append({
            from_id: row[_from_id],
            to_id: tag_to_id[row["_temp_tags"]]
        })

    # BUG: why drop duplicates is needed there ?
    relation_table = pd.DataFrame(relation_data).drop_duplicates()

    return relation_table, right_table

def import_data(engine, df):
    pc = ["code", "name", "quantity", "ingredients_text", "image_url", "image_small_url", "image_ingredients_url", "image_ingredients_small_url", "image_nutrition_url", "image_nutrition_small_url"]
    products = pd.DataFrame(columns=pc)
    products[pc] = df[["code", "product_name", "quantity", "ingredients_text", "image_url", "image_small_url", "image_ingredients_url", "image_ingredients_small_url", "image_nutrition_url", "image_nutrition_small_url"]]
    
    nc = ["product_code", "energy_100g", "fat_100g", "saturated_fat_100g", "sugars_100g", "fiber_100g", "proteins_100g", "salt_100g", "fruits_vegetables_legumes_100g"]
    nutrition = pd.DataFrame(columns=nc)
    nutrition[nc] = df[["code", "energy_100g", "fat_100g", "saturated-fat_100g", "sugars_100g", "fiber_100g", "proteins_100g", "salt_100g", "fruits-vegetables-legumes_100g"]]
    
    sc = ["product_code", "nutriscore", "nutriscore_grade", "nova_group", "environmental_score_grade"]
    score = pd.DataFrame(columns=sc)
    score[sc] = df[["code", "nutriscore_score", "nutriscore_grade", "nova_group", "environmental_score_grade"]]

    products_food_groups, food_groups = get_multi_relationship(
        df[["code", "food_groups_tags"]],
        as_={"code": "product_code"},
        column_to_split="food_groups_tags",
        primary_keys=("code", "food_group_id")
    )
    products_categories, categories = get_multi_relationship(
        df[["code", "categories_tags"]],
        as_={"code": "product_code"},
        column_to_split="categories_tags",
        primary_keys=("code", "category_id")
    )
    products_brands, brands = get_multi_relationship(
        df[["code", "brands_tags"]],
        as_={"code": "product_code"},
        column_to_split="brands_tags",
        primary_keys=("code", "brand_id")
    )
    products_additives, additives = get_multi_relationship(
        df[["code", "additives_tags"]],
        as_={"code": "product_code"},
        column_to_split="additives_tags",
        primary_keys=("code", "additive_id")
    )
    products_labels, labels = get_multi_relationship(
        df[["code", "labels_tags"]],
        as_={"code": "product_code"},
        column_to_split="labels_tags",
        primary_keys=("code", "label_id")
    )
    products_allergens, allergens = get_multi_relationship(
        df[["code", "allergens"]],
        as_={"code": "product_code"},
        column_to_split="allergens",
        primary_keys=("code", "allergen_id")
    )
    products_traces, traces = get_multi_relationship(
        df[["code", "traces_tags"]],
        as_={"code": "product_code"},
        column_to_split="traces_tags",
        primary_keys=("code", "trace_id")
    )
    products_countries, countries = get_multi_relationship(
        df[["code", "countries_tags"]],
        as_={"code": "product_code"},
        column_to_split="countries_tags",
        primary_keys=("code", "country_id")
    )

    products.to_sql("products", engine, if_exists="append", index=False)
    nutrition.to_sql("nutrition", engine, if_exists="append", index=False)
    score.to_sql("score", engine, if_exists="append", index=False)

    food_groups.to_sql("food_groups", engine, if_exists="append", index=False)
    categories.to_sql("categories", engine, if_exists="append", index=False)
    brands.to_sql("brands", engine, if_exists="append", index=False)
    additives.to_sql("additives", engine, if_exists="append", index=False)
    labels.to_sql("labels", engine, if_exists="append", index=False)
    allergens.to_sql("allergens", engine, if_exists="append", index=False)
    traces.to_sql("traces", engine, if_exists="append", index=False)
    countries.to_sql("countries", engine, if_exists="append", index=False)

    products_food_groups.to_sql("products_food_groups", engine, if_exists="append", index=False)
    products_categories.to_sql("products_categories", engine, if_exists="append", index=False)
    products_brands.to_sql("products_brands", engine, if_exists="append", index=False)
    products_additives.to_sql("products_additives", engine, if_exists="append", index=False)
    products_labels.to_sql("products_labels", engine, if_exists="append", index=False)
    products_allergens.to_sql("products_allergens", engine, if_exists="append", index=False)
    products_traces.to_sql("products_traces", engine, if_exists="append", index=False)
    products_countries.to_sql("products_countries", engine, if_exists="append", index=False)


def main(args):
    filename = os.path.abspath(args.filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Le chemin n'existe pas : `{filename}`")
    config = read_database_options(filename)
    engine = init_database(config, args.username, args.password)

    if not args.data_path:
        return
    
    df = read_products_data(args.data_path, config["db_columns"])
    df = clean_products_data(df)

    import_data(engine, df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="NutriscopeDatabaseCreation",
        description="Crée la database pour le Nutriscope",
    )
    parser.add_argument("filename")
    parser.add_argument("-u", "--username", default="postgres")
    # TODO: demander le mdp caché
    parser.add_argument("-pwd", "--password", default="admin")
    # "../data/en.openfoodfacts.org.products.csv"
    parser.add_argument("-d", "--data-path", default=None)
    args = parser.parse_args()
    main(args)