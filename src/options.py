import configparser
from pathlib import Path
import os

DATA_PATH = Path(__file__).parent.parent / "data"

def read_database_options(filename: os.PathLike):
    config_obj = configparser.ConfigParser(allow_no_value=True) # Requis pour autoriser les listes sans valeur
    config_obj.read(filename)

    # convert to dict
    config = {s:dict(config_obj.items(s)) for s in config_obj.sections()}
    config["columns"] = list(config["columns"])
    config["database"]["categories"] = [category.strip() for category in config["database"]["categories"].split(",")]

    return config

CONFIG = read_database_options(
    Path(__file__).with_name("database_options.ini")
)