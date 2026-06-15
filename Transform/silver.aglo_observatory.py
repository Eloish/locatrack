import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from utils.config import load_config
from utils.db import get_engine, get_conn
from utils.geography import clean_text, clean_obs_code


def extract_agglo_obs(engine, years: list) -> pd.DataFrame:
    frames = []
    for annee in years:
        df = pd.read_sql(f"""
            SELECT DISTINCT
                TRIM(UPPER("Observatory")) AS observatory_b,
                TRIM("agglomeration") AS nom_agglomeration
            FROM staging.loyers_{annee}
            WHERE "Observatory" IS NOT NULL
              AND agglomeration IS NOT NULL
        """, engine)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_dim_agglomeration(engine) -> pd.DataFrame:
    df = pd.read_sql("SELECT id_agglomeration, nom_agglomeration FROM silver.dim_agglomeration", engine)
    df["nom_agglomeration"] = df["nom_agglomeration"].apply(clean_text)
    return df


def transform_bridge_agglo(df: pd.DataFrame, dim_agglo: pd.DataFrame) -> pd.DataFrame:
    df["observatory_b"] = df["observatory_b"].apply(clean_obs_code)
    df["nom_agglomeration"] = df["nom_agglomeration"].apply(clean_text)
    df = df.drop_duplicates()

    df_bridge = df.merge(dim_agglo, on="nom_agglomeration", how="left")
    df_bridge = df_bridge.replace({np.nan: None})
    df_bridge = df_bridge.dropna(subset=["id_agglomeration"])
    df_bridge["id_agglomeration"] = df_bridge["id_agglomeration"].astype(int)
    return df_bridge[["observatory_b", "id_agglomeration"]]


def load_bridge_agglo(df: pd.DataFrame, conn):
    cur = conn.cursor()
    try:
        cur.executemany("""
            INSERT INTO silver.bridge_observatoire_agglomeration (observatory_b, id_agglomeration)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, list(df.itertuples(index=False, name=None)))
        conn.commit()
        print(f"[BRIDGE_AGGLO_OBS] {len(df)} relations insérées")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()


def run_silver_agglo_observatory():
    config = load_config()
    years = sorted(
        set(list(config["loyers"]["fichiers_parquet"].keys()) +
            list(config["loyers"]["fichiers_csv"].keys()))
    )
    engine = get_engine()
    conn = get_conn()

    print("[BRIDGE_AGGLO_OBS] Extraction...")
    df = extract_agglo_obs(engine, years)

    print("[BRIDGE_AGGLO_OBS] Chargement dim_agglomeration...")
    dim_agglo = load_dim_agglomeration(engine)

    print("[BRIDGE_AGGLO_OBS] Transformation...")
    df_bridge = transform_bridge_agglo(df, dim_agglo)
    print(f"[BRIDGE_AGGLO_OBS] {len(df_bridge)} relations | {df_bridge['observatory_b'].nunique()} observatoires")

    print("[BRIDGE_AGGLO_OBS] Chargement...")
    load_bridge_agglo(df_bridge, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_agglo_observatory()
