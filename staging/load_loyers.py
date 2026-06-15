import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import pandas as pd
from utils.config import load_config, get_base_dir
from utils.db import get_engine
from utils.validators import validate_file, nettoyer_colonnes_sql
from utils.loader import upsert_to_staging


def extract_loyers(year: int, bronze_dir: str) -> pd.DataFrame:
    path = os.path.join(bronze_dir, f"annee={year}", f"loyers_{year}.parquet")
    if not validate_file(path):
        raise FileNotFoundError(f"[LOYERS] Fichier bronze manquant ou invalide : {path}")
    return pd.read_parquet(path)


def transform_loyers(df: pd.DataFrame) -> pd.DataFrame:
    return nettoyer_colonnes_sql(df)


def load_loyers(year: int, df: pd.DataFrame, engine):
    upsert_to_staging(engine, df, table=f"loyers_{year}")


def run_load_loyers():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["loyers"]["bronze_dir"])
    years = sorted(
        set(list(config["loyers"]["fichiers_parquet"].keys()) +
            list(config["loyers"]["fichiers_csv"].keys()))
    )
    engine = get_engine()

    print("--- Chargement Loyers dans staging ---")
    for year in years:
        df = extract_loyers(year, bronze_dir)
        df = transform_loyers(df)
        load_loyers(year, df, engine)

    print("Loyers staging terminé")


if __name__ == "__main__":
    run_load_loyers()
