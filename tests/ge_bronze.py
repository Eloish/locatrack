"""
Tests qualite Great Expectations -- couche Bronze
Verifie que :
  1. Le fichier parquet a ete cree (telechargement OK)
  2. Il n'est pas vide (conversion OK)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glob
import pandas as pd
import great_expectations as gx
from utils.config import load_config, get_base_dir


def validate_source(name: str, bronze_dir: str) -> bool:
    pattern = os.path.join(bronze_dir, name, "**", "*.parquet")
    files = glob.glob(pattern, recursive=True)

    if not files:
        print(f"[GE BRONZE] {name} : aucun fichier parquet trouve - FAIL")
        return False

    context = gx.get_context(mode="ephemeral")
    all_ok = True

    for f in files:
        df = pd.read_parquet(f)
        fname = os.path.basename(f)

        ds = context.data_sources.add_pandas(name=f"{name}_{fname}")
        asset = ds.add_dataframe_asset(name=fname)
        batch = asset.add_batch_definition_whole_dataframe(fname).get_batch(
            batch_parameters={"dataframe": df}
        )
        suite = context.suites.add(gx.ExpectationSuite(name=f"{name}_{fname}"))
        suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

        result = batch.validate(suite)
        status = "OK" if result.success else "FAIL"
        print(f"[GE BRONZE] {name}/{fname} : {len(df)} lignes - {status}")
        if not result.success:
            all_ok = False

    return all_ok


def run_ge_bronze() -> bool:
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, "data", "bronze")

    sources = ["communes", "dvf", "insee", "loyers"]

    print("[GE BRONZE] Validation couche bronze...")
    results = [validate_source(name, bronze_dir) for name in sources]

    success = all(results)
    print(f"[GE BRONZE] {'SUCCES' if success else 'ECHEC'} -- {sum(results)}/{len(results)} sources OK")
    return success


if __name__ == "__main__":
    ok = run_ge_bronze()
    sys.exit(0 if ok else 1)
