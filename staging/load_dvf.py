import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import io
import os
import pandas as pd
import pyarrow.parquet as pq
from utils.config import load_config, get_base_dir
from utils.db import get_engine, get_conn
from utils.validators import validate_file, nettoyer_colonnes_sql

READ_CHUNK = 100_000


def _create_table(df: pd.DataFrame, table_name: str, engine):
    """Crée la table staging vide à partir du schéma du DataFrame."""
    df.head(0).to_sql(table_name, schema="staging", con=engine, if_exists="replace", index=False)


def _copy_chunk(df: pd.DataFrame, table_name: str, conn):
    """Envoie un chunk via COPY FROM STDIN (CSV stream)."""
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)
    cols = ", ".join(f'"{c}"' for c in df.columns)
    conn.cursor().copy_expert(
        f'COPY staging."{table_name}" ({cols}) FROM STDIN WITH (FORMAT CSV, NULL \'\')',
        buf,
    )
    conn.commit()


def extract_et_load_dvf_year(year: int, bronze_dir: str, engine):
    path = os.path.join(bronze_dir, f"annee={year}", f"dvf_{year}.parquet")
    if not validate_file(path):
        raise FileNotFoundError(f"[DVF] Fichier bronze manquant ou invalide : {path}")

    table_name = f"dvf_{year}"
    pf = pq.ParquetFile(path)
    first = True
    total = 0

    raw_conn = get_conn()
    try:
        for batch in pf.iter_batches(batch_size=READ_CHUNK):
            df = batch.to_pandas()
            df = nettoyer_colonnes_sql(df)
            if first:
                _create_table(df, table_name, engine)
                first = False
            _copy_chunk(df, table_name, raw_conn)
            total += len(df)
    finally:
        raw_conn.close()

    print(f"[DVF] staging.{table_name} — {total} lignes")


def run_load_dvf():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["dvf"]["bronze_dir"])
    years = list(config["dvf"]["fichiers"].keys())
    engine = get_engine()

    print("--- Chargement DVF dans staging ---")
    for year in years:
        extract_et_load_dvf_year(year, bronze_dir, engine)

    print("DVF staging terminé")


if __name__ == "__main__":
    run_load_dvf()
