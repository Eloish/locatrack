import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import pandas as pd
from utils.config import load_config, get_base_dir
from utils.db import get_engine
from utils.validators import validate_file, nettoyer_colonnes_sql
from utils.loader import upsert_to_staging


def extract_dvf(year: int, bronze_dir: str) -> pd.DataFrame:
    path = os.path.join(bronze_dir, f"annee={year}", f"dvf_{year}.parquet")
    if not validate_file(path):
        raise FileNotFoundError(f"[DVF] Fichier bronze manquant ou invalide : {path}")
    return pd.read_parquet(path)


def transform_dvf(df: pd.DataFrame) -> pd.DataFrame:
    return nettoyer_colonnes_sql(df)


def load_dvf(year: int, df: pd.DataFrame, engine):
    upsert_to_staging(engine, df, table=f"dvf_{year}")


def run_load_dvf():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["dvf"]["bronze_dir"])
    years = list(config["dvf"]["fichiers"].keys())
    engine = get_engine()

    print("--- Chargement DVF dans staging ---")
    for year in years:
        df = extract_dvf(year, bronze_dir)
        df = transform_dvf(df)
        load_dvf(year, df, engine)

    print("DVF staging terminé")


if __name__ == "__main__":
    run_load_dvf()
