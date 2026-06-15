import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
from utils.config import get_base_dir
from utils.db import get_conn


def detect_annees(base_dir: str) -> list:
    annees = set()
    for source in ["dvf", "loyers", "insee"]:
        source_dir = os.path.join(base_dir, "data", "bronze", source)
        if not os.path.isdir(source_dir):
            continue
        for entry in os.listdir(source_dir):
            if entry.startswith("annee="):
                try:
                    annees.add(int(entry.split("=", 1)[1]))
                except ValueError:
                    continue
    return sorted(annees)


def load_dim_temps(annees: list, conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS silver.dim_temps (annee INTEGER PRIMARY KEY)
        """)
        for annee in annees:
            cur.execute(
                "INSERT INTO silver.dim_temps (annee) VALUES (%s) ON CONFLICT (annee) DO NOTHING",
                (annee,)
            )
        conn.commit()
        print(f"[DIM_TEMPS] {len(annees)} années insérées")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()


def run_silver_dim_temps():
    base_dir = get_base_dir()
    conn = get_conn()

    print("[DIM_TEMPS] Détection des années...")
    annees = detect_annees(base_dir)
    if not annees:
        raise SystemExit("[DIM_TEMPS] Aucune année détectée dans data/bronze")
    print(f"[DIM_TEMPS] Années : {annees}")

    print("[DIM_TEMPS] Chargement...")
    load_dim_temps(annees, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_dim_temps()
