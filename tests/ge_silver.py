"""
Tests qualite Great Expectations -- couche Silver
Verifie sur chaque table :
  1. Table non vide
  2. Pas de nulls sur les cles primaires
  3. Plages de valeurs coherentes
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import great_expectations as gx
from sqlalchemy import text
from utils.db import get_engine


TABLES = {
    "fact_loyers": {
        "query": "SELECT observatory_b, id_agglomeration, annee, loyer_mensuel_median FROM silver.fact_loyers LIMIT 50000",
        "not_null": ["observatory_b", "id_agglomeration", "annee", "loyer_mensuel_median"],
        "between": {
            "loyer_mensuel_median": (0, 10000),
            "annee": (2010, 2026),
        },
    },
    "dim_commune": {
        "query": "SELECT code_insee, nom_commune FROM silver.dim_commune",
        "not_null": ["code_insee", "nom_commune"],
        "between": {},
    },
    "dim_agglomeration": {
        "query": "SELECT id_agglomeration, nom_agglomeration FROM silver.dim_agglomeration",
        "not_null": ["id_agglomeration", "nom_agglomeration"],
        "between": {},
    },
    "fact_revenus": {
        "query": "SELECT code_insee, annee FROM silver.fact_revenus LIMIT 10000",
        "not_null": ["code_insee", "annee"],
        "between": {
            "annee": (2010, 2026),
        },
    },
    "mapping_uu_agglomeration": {
        "query": "SELECT uu2020, score_fuzzy FROM silver.mapping_uu_agglomeration",
        "not_null": ["uu2020"],
        "between": {
            "score_fuzzy": (0, 100),
        },
    },
}


def validate_table(name: str, config: dict, engine) -> bool:
    with engine.connect() as conn:
        df = pd.read_sql(text(config["query"]), conn)

    context = gx.get_context(mode="ephemeral")
    ds = context.data_sources.add_pandas(name=name)
    asset = ds.add_dataframe_asset(name=name)
    batch = asset.add_batch_definition_whole_dataframe(name).get_batch(
        batch_parameters={"dataframe": df}
    )
    suite = context.suites.add(gx.ExpectationSuite(name=name))

    # Non vide
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # Pas de nulls sur les cles
    for col in config["not_null"]:
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # Plages de valeurs
    for col, (mn, mx) in config["between"].items():
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
            column=col, min_value=mn, max_value=mx
        ))

    result = batch.validate(suite)
    passed = sum(1 for r in result.results if r.success)
    failed = sum(1 for r in result.results if not r.success)
    status = "OK" if result.success else "FAIL"
    print(f"[GE SILVER] {name} : {len(df)} lignes, {passed} OK / {failed} FAIL - {status}")
    if not result.success:
        for r in result.results:
            if not r.success:
                print(f"  !! {r.expectation_config.type} ({r.result})")
    return result.success


def run_ge_silver() -> bool:
    engine = get_engine()
    print("[GE SILVER] Validation couche silver...")
    results = [validate_table(name, config, engine) for name, config in TABLES.items()]
    success = all(results)
    print(f"[GE SILVER] {'SUCCES' if success else 'ECHEC'} -- {sum(results)}/{len(results)} tables OK")
    return success


if __name__ == "__main__":
    ok = run_ge_silver()
    sys.exit(0 if ok else 1)
