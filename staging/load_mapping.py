import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import pandas as pd
from sqlalchemy import text
from utils.config import get_base_dir
from utils.db import get_engine
from utils.geography import clean_text
from utils.validators import validate_columns


def extract_mapping(base_dir: str) -> pd.DataFrame:
    path = os.path.join(base_dir, "data/mapping_observatory_communes.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"[MAPPING] Fichier introuvable : {path}")
    return pd.read_csv(path, encoding="cp1252", dtype=str)


def transform_mapping(df: pd.DataFrame) -> pd.DataFrame:
    validate_columns(df, ["code_insee", "observatory_b"], source="mapping")

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(clean_text)

    df["code_insee"] = df["code_insee"].astype(str).str.zfill(5)
    df = df.drop_duplicates(subset=["code_insee", "observatory_b"])
    return df


def load_mapping(df: pd.DataFrame, engine):
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ref"))
    df.to_sql("mapping_communes", con=engine, schema="ref", if_exists="replace", index=False)
    print(f"[MAPPING] ref.mapping_communes — {len(df)} lignes chargées")


def run_load_mapping():
    base_dir = get_base_dir()
    engine = get_engine()

    print("--- Chargement Mapping dans ref ---")
    df = extract_mapping(base_dir)
    df = transform_mapping(df)
    load_mapping(df, engine)
    print("Mapping terminé")


if __name__ == "__main__":
    run_load_mapping()
