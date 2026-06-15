import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(script_path: str):
    print(f"\n{'─'*50}")
    print(f"  {script_path}")
    print(f"{'─'*50}")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, script_path)],
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"\n[PIPELINE] Erreur dans {script_path} — pipeline arrêté")
        sys.exit(1)


def run_dbt():
    print(f"\n{'─'*50}")
    print("  dbt run (Gold layer)")
    print(f"{'─'*50}")
    result = subprocess.run(
        ["dbt", "run"],
        cwd=os.path.join(BASE_DIR, "dbt"),
        capture_output=False,
    )
    if result.returncode != 0:
        print("\n[PIPELINE] Erreur dbt — pipeline arrêté")
        sys.exit(1)


def run_migrations():
    from utils.db import get_conn
    from utils.run_log import ensure_run_log_table
    conn = get_conn()
    ensure_run_log_table(conn)
    conn.close()
    print("[PIPELINE] Migrations OK")


def main():
    print("=" * 50)
    print("  LOCATRACK PIPELINE")
    print("=" * 50)

    run_migrations()

    # ── BRONZE ───────────────────────────────────────────
    print("\n[1/4] BRONZE — Ingestion des sources")
    run_script("ingestion/ingest_dvf.py")
    run_script("ingestion/ingest_loyers.py")
    run_script("ingestion/ingest_insee.py")
    run_script("ingestion/ingest_communes.py")
    run_script("ingestion/ingest_zonages.py")

    # ── STAGING ──────────────────────────────────────────
    print("\n[2/4] STAGING — Chargement en base")
    run_script("staging/load_dvf.py")
    run_script("staging/load_loyers.py")
    run_script("staging/load_insee.py")
    run_script("staging/load_communes.py")
    run_script("staging/load_zonages.py")
    run_script("staging/load_mapping.py")

    # ── SILVER ───────────────────────────────────────────
    # Ordre important : dimensions avant faits, bridge en dernier
    print("\n[3/4] SILVER — Transformation")
    run_script("Transform/silver_dim_temps.py")
    run_script("Transform/silver_dim_commune.py")
    run_script("Transform/silver_dim_observatoire.py")
    run_script("Transform/silver_dim_agglomeration.py")
    run_script("Transform/silver_dim_type_bien.py")
    run_script("Transform/silver_bridge_commune_observatoire.py")
    run_script("Transform/silver.aglo_observatory.py")
    run_script("Transform/silver_fact_loyers.py")
    run_script("Transform/silver_fact_revenus.py")
    run_script("Transform/silver_fact_transactions.py")

    # ── GOLD ─────────────────────────────────────────────
    print("\n[4/4] GOLD — Modèles dbt")
    run_dbt()

    print("\n" + "=" * 50)
    print("  PIPELINE LOCATRACK COMPLET")
    print("=" * 50)


if __name__ == "__main__":
    main()
