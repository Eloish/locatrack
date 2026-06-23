import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hashlib
import pandas as pd
from psycopg2.extras import execute_values
from utils.config import load_config
from utils.db import get_engine, get_conn
from utils.geography import clean_text
from utils.validators import validate_not_null


def stable_id(nom: str) -> int:
    """ID stable dérivé du nom : même nom → même ID partout (local, Docker, CI)."""
    return int(hashlib.md5(nom.encode()).hexdigest(), 16) % 2_000_000_000


def extract_agglomerations(engine, years: list) -> pd.DataFrame:
    frames = []
    for annee in years:
        print(f"[DIM_AGGLO] Extraction staging.loyers_{annee}...")
        df = pd.read_sql(f"""
            SELECT DISTINCT agglomeration
            FROM staging.loyers_{annee}
            WHERE agglomeration IS NOT NULL
        """, engine)
        df["agglomeration"] = df["agglomeration"].apply(clean_text)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def transform_dim_agglomeration(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna().drop_duplicates()
    df = df.rename(columns={"agglomeration": "nom_agglomeration"})
    df = validate_not_null(df, ["nom_agglomeration"], source="dim_agglomeration")
    df["id_agglomeration"] = df["nom_agglomeration"].apply(stable_id)
    return df


def load_dim_agglomeration(df: pd.DataFrame, conn):
    cur = conn.cursor()
    try:
        values = [(int(row["id_agglomeration"]), row["nom_agglomeration"]) for _, row in df.iterrows()]
        execute_values(cur, """
            INSERT INTO silver.dim_agglomeration (id_agglomeration, nom_agglomeration)
            VALUES %s
            ON CONFLICT (nom_agglomeration) DO NOTHING
        """, values)
        conn.commit()
        print(f"[DIM_AGGLO] {len(values)} agglomérations insérées (ON CONFLICT IGNORE)")
    except Exception as e:
        conn.rollback()
        print(f"[DIM_AGGLO] Erreur : {e}")
        raise
    finally:
        cur.close()


def run_silver_dim_agglomeration():
    config = load_config()
    years = sorted(
        set(list(config["loyers"]["fichiers_parquet"].keys()) +
            list(config["loyers"]["fichiers_csv"].keys()))
    )
    engine = get_engine()
    conn = get_conn()

    print("[DIM_AGGLO] Extraction...")
    df = extract_agglomerations(engine, years)

    print("[DIM_AGGLO] Transformation...")
    df = transform_dim_agglomeration(df)
    print(f"[DIM_AGGLO] {len(df)} agglomérations uniques")

    print("[DIM_AGGLO] Chargement...")
    load_dim_agglomeration(df, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_dim_agglomeration()
