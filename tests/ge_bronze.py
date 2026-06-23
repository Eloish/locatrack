"""
Tests qualite Great Expectations -- couche Bronze
Verifie que :
  1. Le fichier parquet a ete cree (telechargement OK)
  2. Il n'est pas vide (conversion OK)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glob
import pyarrow.parquet as pq
from utils.config import load_config, get_base_dir


def validate_source(name: str, bronze_dir: str) -> bool:
    pattern = os.path.join(bronze_dir, name, "**", "*.parquet")
    files = glob.glob(pattern, recursive=True)

    if not files:
        print(f"[GE BRONZE] {name} : aucun fichier parquet trouve - FAIL")
        return False

    all_ok = True
    for f in files:
        fname = os.path.basename(f)
        # Lecture des metadonnees uniquement — sans charger les donnees en memoire
        meta = pq.read_metadata(f)
        num_rows = meta.num_rows
        status = "OK" if num_rows > 0 else "FAIL"
        print(f"[GE BRONZE] {name}/{fname} : {num_rows} lignes - {status}")
        if num_rows == 0:
            all_ok = False

    return all_ok


def validate_files(name: str, bronze_dir: str, extensions: list) -> bool:
    """Valide les sources non-parquet (CSV, ZIP) : existence + non vide."""
    pattern_base = os.path.join(bronze_dir, name)
    files = []
    for ext in extensions:
        files += glob.glob(os.path.join(pattern_base, "**", f"*.{ext}"), recursive=True)
    files = list(set(files))

    if not files:
        print(f"[GE BRONZE] {name} : aucun fichier {extensions} trouve - FAIL")
        return False

    all_ok = True
    for f in files:
        size = os.path.getsize(f)
        status = "OK" if size > 0 else "FAIL"
        print(f"[GE BRONZE] {name}/{os.path.basename(f)} : {size} octets - {status}")
        if size == 0:
            all_ok = False

    return all_ok


def run_ge_bronze() -> bool:
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, "data", "bronze")

    parquet_sources = ["communes", "dvf", "insee", "loyers"]
    csv_sources = ["loyers_zonages"]
    zip_sources = ["ref_geo"]

    print("[GE BRONZE] Validation couche bronze...")
    results = []
    results += [validate_source(name, bronze_dir) for name in parquet_sources]
    results += [validate_files(name, bronze_dir, ["csv"]) for name in csv_sources]
    results += [validate_files(name, bronze_dir, ["zip"]) for name in zip_sources]

    total = len(parquet_sources) + len(csv_sources) + len(zip_sources)
    success = all(results)
    print(f"[GE BRONZE] {'SUCCES' if success else 'ECHEC'} -- {sum(results)}/{total} sources OK")
    return success


if __name__ == "__main__":
    ok = run_ge_bronze()
    sys.exit(0 if ok else 1)
