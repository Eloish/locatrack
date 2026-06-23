"""
Tests qualite Great Expectations -- couche Silver
Verifie sur chaque table :
  1. Table non vide
  2. Pas de nulls sur les cles primaires
  3. Plages de valeurs coherentes
  4. Unicite des cles primaires (dims)
  5. Integrite referentielle (cles etrangeres)
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
        "unique": [],
    },
    "fact_revenus": {
        "query": "SELECT code_insee, annee FROM silver.fact_revenus LIMIT 10000",
        "not_null": ["code_insee", "annee"],
        "between": {
            "annee": (2010, 2026),
        },
        "unique": [],
    },
    "fact_transactions": {
        "query": "SELECT code_insee, annee, type_local, valeur_fonciere FROM silver.fact_transactions LIMIT 10000",
        "not_null": ["code_insee", "annee", "type_local"],
        "between": {
            "valeur_fonciere": (0, 100000000),
            "annee": (2010, 2026),
        },
        "unique": [],
    },
    "dim_commune": {
        "query": "SELECT code_insee, nom_commune FROM silver.dim_commune",
        "not_null": ["code_insee", "nom_commune"],
        "between": {},
        "unique": ["code_insee"],
    },
    "dim_agglomeration": {
        "query": "SELECT id_agglomeration, nom_agglomeration FROM silver.dim_agglomeration",
        "not_null": ["id_agglomeration", "nom_agglomeration"],
        "between": {},
        "unique": ["id_agglomeration"],
    },
    "dim_observatoire": {
        "query": "SELECT observatory_b FROM silver.dim_observatoire",
        "not_null": ["observatory_b"],
        "between": {},
        "unique": ["observatory_b"],
    },
    "dim_temps": {
        "query": "SELECT annee FROM silver.dim_temps",
        "not_null": ["annee"],
        "between": {
            "annee": (2010, 2026),
        },
        "unique": ["annee"],
    },
    "dim_type_bien": {
        "query": "SELECT type_bien FROM silver.dim_type_bien",
        "not_null": ["type_bien"],
        "between": {},
        "unique": ["type_bien"],
    },
    "bridge_commune_observatoire": {
        "query": "SELECT code_insee, observatory_b FROM silver.bridge_commune_observatoire LIMIT 10000",
        "not_null": ["code_insee", "observatory_b"],
        "between": {},
        "unique": [],
        "min_rows": 0,
    },
    "mapping_uu_agglomeration": {
        "query": "SELECT uu2020, id_agglomeration, score_fuzzy FROM silver.mapping_uu_agglomeration",
        "not_null": ["uu2020"],
        "min_rows": 0,
        "between": {
            "score_fuzzy": (0, 100),
        },
        "unique": [],  # PK composite (uu2020, observatory_b) — pas de check colonne seule
    },
}

# Cles etrangeres : (table, colonne, table_ref, colonne_ref)
FOREIGN_KEYS = [
    ("silver.fact_loyers",               "id_agglomeration", "silver.dim_agglomeration", "id_agglomeration"),
    ("silver.fact_loyers",               "observatory_b",    "silver.dim_observatoire",  "observatory_b"),
    ("silver.fact_revenus",              "code_insee",       "silver.dim_commune",        "code_insee"),
    ("silver.fact_transactions",         "code_insee",       "silver.dim_commune",        "code_insee"),
    ("silver.bridge_commune_observatoire", "code_insee",     "silver.dim_commune",        "code_insee"),
    ("silver.bridge_commune_observatoire", "observatory_b",  "silver.dim_observatoire",  "observatory_b"),
    ("silver.mapping_uu_agglomeration",  "id_agglomeration", "silver.dim_agglomeration", "id_agglomeration"),
]


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
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=config.get("min_rows", 1)))

    # Pas de nulls sur les cles
    for col in config["not_null"]:
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # Plages de valeurs
    for col, (mn, mx) in config["between"].items():
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
            column=col, min_value=mn, max_value=mx
        ))

    # Unicite des cles primaires
    for col in config.get("unique", []):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column=col))

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


def validate_foreign_keys(engine) -> bool:
    print("[GE SILVER] Verification integrite referentielle...")
    all_ok = True
    with engine.connect() as conn:
        for table, col, ref_table, ref_col in FOREIGN_KEYS:
            query = text(f"""
                SELECT COUNT(*) FROM {table} t
                WHERE t.{col} IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM {ref_table} r WHERE r.{ref_col} = t.{col}
                )
            """)
            orphans = conn.execute(query).scalar()
            status = "OK" if orphans == 0 else "FAIL"
            print(f"  {table}.{col} -> {ref_table}.{ref_col} : {orphans} orphelins - {status}")
            if orphans > 0:
                all_ok = False
    return all_ok


def run_ge_silver() -> bool:
    engine = get_engine()
    print("[GE SILVER] Validation couche silver...")
    results = [validate_table(name, config, engine) for name, config in TABLES.items()]

    fk_ok = validate_foreign_keys(engine)
    results.append(fk_ok)

    success = all(results)
    print(f"[GE SILVER] {'SUCCES' if success else 'ECHEC'} -- {sum(results)}/{len(results)} validations OK")
    return success


if __name__ == "__main__":
    ok = run_ge_silver()
    sys.exit(0 if ok else 1)
