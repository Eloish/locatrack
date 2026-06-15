import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import pandas as pd
from utils.config import load_config, get_base_dir
from utils.db import get_engine
from utils.validators import validate_file, nettoyer_colonnes_sql
from utils.loader import upsert_to_staging


def extract_communes(bronze_dir: str) -> pd.DataFrame:
    path = os.path.join(bronze_dir, "communes.parquet")
    if not validate_file(path):
        raise FileNotFoundError(f"[COMMUNES] Fichier bronze manquant ou invalide : {path}")
    return pd.read_parquet(path)


def transform_communes(df: pd.DataFrame) -> pd.DataFrame:
    return nettoyer_colonnes_sql(df)


def load_communes(df: pd.DataFrame, engine):
    upsert_to_staging(engine, df, table="communes")


def run_load_communes():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["communes"]["bronze_dir"])
    engine = get_engine()

    print("--- Chargement Communes dans staging ---")
    df = extract_communes(bronze_dir)
    df = transform_communes(df)
    load_communes(df, engine)
    print("Communes staging terminé")


if __name__ == "__main__":
    run_load_communes()
