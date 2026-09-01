import argparse
import os
import sqlparse
import configparser
from sqlalchemy import create_engine, URL
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.schema import CreateTable
import pandas as pd


def read_database_options(filename):
    config = configparser.ConfigParser(allow_no_value=True) # Requis pour autoriser les listes sans valeur
    config.read(filename)

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

def main(args):
    filename = os.path.abspath(args.filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Le chemin n'existe pas : `{filename}`")
    config = read_database_options(filename)
    engine = init_database(config, args.username, args.password)
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="NutriscopeDatabaseCreation",
        description="Crée la database pour le Nutriscope",
    )
    parser.add_argument("filename")
    parser.add_argument("-u", "--username", default="postgres")
    # TODO: demander le mdp caché
    parser.add_argument("-pwd", "--password", default="admin")
    args = parser.parse_args()
    main(args)