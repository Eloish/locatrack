import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from utils.config import load_config
from utils.db import get_engine, get_conn
from utils.validators import validate_not_null, validate_fk, nettoyer_float
from utils.loader import copy_to_postgres

COLUMNS = ["code_insee", "annee", "revenu_median", "revenu_mensuel"]

COL_REVENU_PAR_ANNEE = {
    2017: "Q217",
    2018: "Q218",
    2019: "Q219",
    2020: "Q220",
    2021: "Q221",
}


def extract_revenus(engine) -> pd.DataFrame:
    frames = []
    for annee, col_revenu in COL_REVENU_PAR_ANNEE.items():
        print(f"[FACT_REVENUS] Extraction INSEE {annee} ({col_revenu})...")
        df = pd.read_sql(f"""
            SELECT
                "CODGEO" as code_insee,
                "{col_revenu}"::text as revenu_median
            FROM staging.insee_{annee}
            WHERE "{col_revenu}"::text != 's'
              AND "{col_revenu}" IS NOT NULL
        """, engine)
        df["annee"] = annee
        frames.append(df)
        print(f"[FACT_REVENUS] {annee} : {len(df)} communes")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def transform_fact_revenus(df: pd.DataFrame) -> pd.DataFrame:
    df["revenu_median"] = nettoyer_float(df["revenu_median"])
    df = validate_not_null(df, ["code_insee", "revenu_median"], source="fact_revenus")
    df["revenu_mensuel"] = df["revenu_median"] / 12
    df["code_insee"] = df["code_insee"].astype(str).str.strip().str.zfill(5)
    return df[COLUMNS]


def load_fact_revenus(df: pd.DataFrame, engine, conn):
    valid_insee = set(
        pd.read_sql("SELECT code_insee FROM silver.dim_commune", engine)["code_insee"].astype(str)
    )
    df = validate_fk(df, "code_insee", valid_insee, source="fact_revenus")
    copy_to_postgres(conn, df, schema="silver", table="fact_revenus", columns=COLUMNS)


def run_silver_fact_revenus():
    engine = get_engine()
    conn = get_conn()

    print("[FACT_REVENUS] Extraction...")
    df = extract_revenus(engine)

    print("[FACT_REVENUS] Transformation...")
    df = transform_fact_revenus(df)
    print(f"[FACT_REVENUS] {len(df)} lignes")

    print("[FACT_REVENUS] Chargement...")
    load_fact_revenus(df, engine, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_fact_revenus()
