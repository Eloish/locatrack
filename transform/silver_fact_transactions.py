import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from utils.config import load_config
from utils.db import get_engine, get_conn
from utils.geography import normaliser_insee
from utils.validators import validate_not_null, validate_range, validate_fk, nettoyer_float
from utils.loader import copy_to_postgres

COLUMNS = [
    "code_insee", "annee", "type_local", "nature_mutation",
    "valeur_fonciere", "surface_bati", "surface_terrain",
    "nombre_pieces", "prix_m2", "nature_culture",
]


def extract_dvf(engine, years: list) -> pd.DataFrame:
    frames = []
    for annee in years:
        print(f"[FACT_TRANSACTIONS] Extraction DVF {annee}...")
        df = pd.read_sql(f"""
            SELECT
                "Code_commune" as com,
                "Code_departement" as dep,
                EXTRACT(YEAR FROM TO_DATE("Date_mutation", 'DD/MM/YYYY')) as annee,
                "Nature_mutation" as nature_mutation,
                "Type_local" as type_local,
                REPLACE("Valeur_fonciere", ',', '.')::FLOAT as valeur_fonciere,
                "Surface_reelle_bati" as surface_bati,
                "Surface_terrain" as surface_terrain,
                "Nombre_pieces_principales" as nombre_pieces,
                "Nature_culture" as nature_culture
            FROM staging.dvf_{annee}
            WHERE "Nature_mutation" = 'Vente'
              AND "Type_local" IS NOT NULL
              AND "Surface_reelle_bati" > 0
              AND "Valeur_fonciere" IS NOT NULL
        """, engine)
        frames.append(df)
        print(f"[FACT_TRANSACTIONS] DVF {annee} : {len(df)} lignes")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def transform_fact_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df["code_insee"] = df.apply(lambda x: normaliser_insee(x["dep"], x["com"]), axis=1)

    for col in ["valeur_fonciere", "surface_bati", "surface_terrain", "nombre_pieces"]:
        df[col] = nettoyer_float(df[col])

    df["annee"] = df["annee"].astype("Int64")
    df["prix_m2"] = df["valeur_fonciere"] / df["surface_bati"]

    df = validate_not_null(df, ["code_insee", "annee", "valeur_fonciere", "surface_bati"], source="fact_transactions")
    df = validate_range(df, "prix_m2", min_val=0, max_val=100_000, source="fact_transactions")
    df = validate_range(df, "surface_bati", min_val=1, source="fact_transactions")

    return df[COLUMNS]


def load_fact_transactions(df: pd.DataFrame, engine, conn):
    valid_insee = set(
        pd.read_sql("SELECT code_insee FROM silver.dim_commune", engine)["code_insee"].astype(str)
    )
    df = validate_fk(df, "code_insee", valid_insee, source="fact_transactions")
    copy_to_postgres(conn, df, schema="silver", table="fact_transactions", columns=COLUMNS)


def run_silver_fact_transactions():
    config = load_config()
    years = list(config["dvf"]["fichiers"].keys())
    engine = get_engine()
    conn = get_conn()

    print("[FACT_TRANSACTIONS] Extraction...")
    df = extract_dvf(engine, years)

    print("[FACT_TRANSACTIONS] Transformation...")
    df = transform_fact_transactions(df)

    print("[FACT_TRANSACTIONS] Chargement...")
    load_fact_transactions(df, engine, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_fact_transactions()
