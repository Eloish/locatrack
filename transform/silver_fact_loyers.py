import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from utils.config import load_config
from utils.db import get_engine, get_conn
from utils.geography import clean_obs_code
from utils.validators import validate_not_null, validate_range
from utils.loader import copy_to_postgres

COLUMNS = [
    "observatory_b", "id_agglomeration", "annee", "type_habitat",
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
    raise ValueError(f"[FACT_LOYERS] Colonne nombre_observations introuvable dans staging.loyers_{annee}")


def extract_loyers(engine, years: list) -> pd.DataFrame:
    frames = []
    for annee in years:
        print(f"[FACT_LOYERS] Extraction staging.loyers_{annee}...")
        col_obs = get_col_observations(engine, annee)
        df = pd.read_sql(f"""
            SELECT
                TRIM(UPPER("Observatory"))                              AS observatory_b,
                TRIM("agglomeration")                                   AS nom_agglomeration,
                "Data_year"                                             AS annee,
                COALESCE(TRIM("Type_habitat"), 'Ensemble')              AS type_habitat,
                COALESCE(TRIM("nombre_pieces_homogene"), 'Tous')        AS nombre_pieces,
                "loyer_mensuel_median",
                "loyer_median"                                          AS loyer_median_m2,
                "{col_obs}"                                             AS nombre_observations
            FROM staging.loyers_{annee}
            WHERE "Observatory" IS NOT NULL
              AND "agglomeration" IS NOT NULL
        """, engine)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_agglomeration_mapping(engine) -> dict:
    df = pd.read_sql("SELECT id_agglomeration, nom_agglomeration FROM silver.dim_agglomeration", engine)
    return dict(zip(df["nom_agglomeration"].str.strip(), df["id_agglomeration"]))


def transform_fact_loyers(df: pd.DataFrame, agglo_mapping: dict) -> pd.DataFrame:
    df["observatory_b"] = df["observatory_b"].apply(clean_obs_code)

    # Normaliser nombre_pieces : "4P et plus" → "4P+"
    df["nombre_pieces"] = (
        df["nombre_pieces"]
        .str.replace(r"\s*et\s+plus\s*$", "+", regex=True)
        .str.strip()
    )

    # Jointure avec dim_agglomeration via le nom
    df["id_agglomeration"] = df["nom_agglomeration"].str.strip().map(agglo_mapping)

    for col in ["loyer_mensuel_median", "loyer_median_m2", "nombre_observations"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Log les agglomérations non matchées
    non_matches = df[df["id_agglomeration"].isna()]["nom_agglomeration"].unique()
    if len(non_matches) > 0:
        print(f"[FACT_LOYERS] {len(non_matches)} agglomérations non matchées : {non_matches[:5]}")

    df = validate_not_null(df, ["observatory_b", "id_agglomeration", "annee"], source="fact_loyers")
    df = validate_range(df, "loyer_mensuel_median", min_val=0, source="fact_loyers")
    df = validate_range(df, "loyer_median_m2", min_val=0, source="fact_loyers")

    df["id_agglomeration"] = df["id_agglomeration"].astype(int)

    return df[COLUMNS].drop_duplicates(subset=["observatory_b", "id_agglomeration", "annee", "type_habitat", "nombre_pieces"])


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

    print("[FACT_LOYERS] Chargement mapping agglomérations...")
    agglo_mapping = load_agglomeration_mapping(engine)
    print(f"[FACT_LOYERS] {len(agglo_mapping)} agglomérations dans dim_agglomeration")

    print("[FACT_LOYERS] Extraction...")
    df = extract_loyers(engine, years)

    print("[FACT_LOYERS] Transformation...")
    df = transform_fact_loyers(df, agglo_mapping)
    print(f"[FACT_LOYERS] {len(df)} lignes finales")

    print("[FACT_LOYERS] Chargement...")
    load_fact_loyers(df, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_fact_loyers()
