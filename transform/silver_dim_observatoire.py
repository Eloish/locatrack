import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from utils.config import load_config
from utils.db import get_engine, get_conn
from utils.geography import clean_obs_code
from utils.validators import validate_not_null
from utils.loader import copy_to_postgres

COLUMNS = ["observatory_b"]


def extract_observatoires(engine, years: list) -> pd.DataFrame:
    frames = []
    for annee in years:
        df = pd.read_sql(f"""
            SELECT DISTINCT TRIM(UPPER("Observatory")) AS observatory_b
            FROM staging.loyers_{annee}
            WHERE "Observatory" IS NOT NULL
        """, engine)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def transform_dim_observatoire(df: pd.DataFrame) -> pd.DataFrame:
    df["observatory_b"] = df["observatory_b"].apply(clean_obs_code)
    df = df.drop_duplicates()
    df = validate_not_null(df, ["observatory_b"], source="dim_observatoire")
    return df[COLUMNS]


def load_dim_observatoire(df: pd.DataFrame, conn):
    copy_to_postgres(conn, df, schema="silver", table="dim_observatoire", columns=COLUMNS)


def run_silver_dim_observatoire():
    config = load_config()
    years = sorted(
        set(list(config["loyers"]["fichiers_parquet"].keys()) +
            list(config["loyers"]["fichiers_csv"].keys()))
    )
    engine = get_engine()
    conn = get_conn()

    print("[DIM_OBS] Extraction...")
    df = extract_observatoires(engine, years)

    print("[DIM_OBS] Transformation...")
    df = transform_dim_observatoire(df)
    print(f"[DIM_OBS] {len(df)} observatoires")

    print("[DIM_OBS] Chargement...")
    load_dim_observatoire(df, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_dim_observatoire()
