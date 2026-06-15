import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from utils.config import load_config
from utils.db import get_engine, get_conn
from utils.geography import clean_obs_code
from utils.validators import validate_not_null, validate_range
from utils.loader import copy_to_postgres

COLUMNS = [
    "observatory_b", "annee", "type_habitat",
    "nombre_pieces", "loyer_mensuel_median", "loyer_median_m2", "nombre_observations",
]


def get_col_observations(engine, annee: int) -> str:
    cols = pd.read_sql("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'staging' AND table_name = %(table)s
    """, engine, params={"table": f"loyers_{annee}"})["column_name"].tolist()
    for candidate in ["nombre_observations", "nombre_obsservations"]:
        if candidate in cols:
            return candidate
    raise ValueError(f"[FACT_LOYERS] Colonne nombre_observations introuvable dans staging.loyers_{annee} — colonnes : {cols}")


def extract_loyers(engine, years: list) -> pd.DataFrame:
    frames = []
    for annee in years:
        print(f"[FACT_LOYERS] Extraction staging.loyers_{annee}...")
        col_obs = get_col_observations(engine, annee)
        df = pd.read_sql(f"""
            SELECT
                TRIM(UPPER("Observatory")) AS observatory_b,
                "Data_year" AS annee,
                "Type_habitat" AS type_habitat,
                "nombre_pieces_homogene" AS nombre_pieces,
                "loyer_mensuel_median",
                "loyer_median" AS loyer_median_m2,
                "{col_obs}" AS nombre_observations
            FROM staging.loyers_{annee}
            WHERE "Observatory" IS NOT NULL
        """, engine)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def transform_fact_loyers(df: pd.DataFrame) -> pd.DataFrame:
    df["observatory_b"] = df["observatory_b"].apply(clean_obs_code)

    for col in ["loyer_mensuel_median", "loyer_median_m2", "nombre_observations"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = validate_not_null(df, ["observatory_b", "annee"], source="fact_loyers")
    df = validate_range(df, "loyer_mensuel_median", min_val=0, source="fact_loyers")
    df = validate_range(df, "loyer_median_m2", min_val=0, source="fact_loyers")

    return df[COLUMNS]


def load_fact_loyers(df: pd.DataFrame, conn):
    copy_to_postgres(conn, df, schema="silver", table="fact_loyers", columns=COLUMNS)


def run_silver_fact_loyers():
    config = load_config()
    years = sorted(
        set(list(config["loyers"]["fichiers_parquet"].keys()) +
            list(config["loyers"]["fichiers_csv"].keys()))
    )
    engine = get_engine()
    conn = get_conn()

    print("[FACT_LOYERS] Extraction...")
    df = extract_loyers(engine, years)

    print("[FACT_LOYERS] Transformation...")
    df = transform_fact_loyers(df)
    print(f"[FACT_LOYERS] {len(df)} lignes finales")

    print("[FACT_LOYERS] Chargement...")
    load_fact_loyers(df, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_fact_loyers()
