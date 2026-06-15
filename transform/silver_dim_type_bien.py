import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import pandas as pd
from utils.config import load_config, get_base_dir
from utils.db import get_engine, get_conn
from utils.validators import validate_not_null


def detect_dvf_years(base_dir: str) -> list:
    dvf_dir = os.path.join(base_dir, "data", "bronze", "dvf")
    years = []
    if os.path.isdir(dvf_dir):
        for entry in os.listdir(dvf_dir):
            if entry.startswith("annee="):
                try:
                    years.append(int(entry.split("=", 1)[1]))
                except ValueError:
                    continue
    return sorted(years)


def extract_types_bien(engine, years: list) -> list:
    all_types = set()
    for annee in years:
        print(f"[DIM_TYPE_BIEN] Lecture staging.dvf_{annee}...")
        df = pd.read_sql(f"""
            SELECT DISTINCT "Type_local" as type_bien
            FROM staging.dvf_{annee}
            WHERE "Type_local" IS NOT NULL
        """, engine)
        all_types.update(df["type_bien"].dropna().astype(str).tolist())
    return sorted(all_types)


def load_dim_type_bien(types: list, conn):
    cur = conn.cursor()
    try:
        for type_bien in types:
            cur.execute(
                "INSERT INTO silver.dim_type_bien (type_bien) VALUES (%s) ON CONFLICT (type_bien) DO NOTHING",
                (type_bien,)
            )
        conn.commit()
        print(f"[DIM_TYPE_BIEN] {len(types)} types insérés")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()


def run_silver_dim_type_bien():
    base_dir = get_base_dir()
    engine = get_engine()
    conn = get_conn()

    print("[DIM_TYPE_BIEN] Détection des années DVF...")
    years = detect_dvf_years(base_dir)
    if not years:
        raise SystemExit("[DIM_TYPE_BIEN] Aucune année DVF trouvée dans data/bronze/dvf")
    print(f"[DIM_TYPE_BIEN] Années : {years}")

    print("[DIM_TYPE_BIEN] Extraction des types...")
    types = extract_types_bien(engine, years)
    print(f"[DIM_TYPE_BIEN] Types détectés : {types}")

    print("[DIM_TYPE_BIEN] Chargement...")
    load_dim_type_bien(types, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_dim_type_bien()
