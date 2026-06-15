import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from utils.db import get_engine, get_conn
from utils.validators import validate_fk

CANDIDATS_INSEE = ["INSEE", "CODE INSEE", "L6A", "CODE_INSEE", "COMMUNE"]
COLUMNS = ["code_insee", "observatory_b"]

# Arrondissements Paris (75101-75120), Lyon (69381-69389), Marseille (13201-13216)
def normaliser_arrondissement(code: str) -> str:
    if code.startswith("751") and len(code) == 5:
        return "75056"
    if code.startswith("6938") and len(code) == 5:
        return "69123"
    if code.startswith("132") and len(code) == 5 and int(code) >= 13201:
        return "13055"
    return code


def load_valid_sets(engine) -> tuple[set, set]:
    set_commune = set(
        pd.read_sql("SELECT code_insee FROM silver.dim_commune", engine)["code_insee"].astype(str).str.strip()
    )
    set_obs = set(
        pd.read_sql("SELECT observatory_b FROM silver.dim_observatoire", engine)["observatory_b"].astype(str).str.strip()
    )
    return set_commune, set_obs


def get_zonage_tables(conn) -> list:
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'staging' AND table_name LIKE 'zonage_b%'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    return tables


def extract_bridge(engine, conn) -> pd.DataFrame:
    tables = get_zonage_tables(conn)
    print(f"[BRIDGE_COMMUNE_OBS] {len(tables)} tables zonage trouvées")
    rows = []

    for table in tables:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'staging' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        cols_clean = {c.strip().upper(): c for c, in cur.fetchall()}
        cur.close()

        obs_code = table.replace("zonage_", "").upper()
        col_insee = next((cols_clean[c.upper()] for c in CANDIDATS_INSEE if c.upper() in cols_clean), None)
        if col_insee is None:
            print(f"[BRIDGE_COMMUNE_OBS] {table} — colonne INSEE non trouvée, ignoré")
            continue

        try:
            df = pd.read_sql(f"""
                SELECT DISTINCT TRIM("{col_insee}") AS code_insee
                FROM staging.{table}
                WHERE "{col_insee}" IS NOT NULL
            """, engine)
            df["code_insee"] = df["code_insee"].astype(str).str.strip().str.zfill(5)
            df = df[df["code_insee"].str.match(r'^(\d{5}|2[AB]\d{3})$')]
            # Normaliser arrondissements → commune principale
            df["code_insee"] = df["code_insee"].apply(normaliser_arrondissement)
            df["observatory_b"] = obs_code
            rows.append(df)
            print(f"[BRIDGE_COMMUNE_OBS] {table} → {len(df)} communes")
        except Exception as e:
            print(f"[BRIDGE_COMMUNE_OBS] {table} ignoré : {e}")

    return pd.concat(rows, ignore_index=True).drop_duplicates() if rows else pd.DataFrame()


def transform_bridge(df: pd.DataFrame, set_commune: set, set_obs: set) -> pd.DataFrame:
    df = validate_fk(df, "code_insee", set_commune, source="bridge_commune_obs")
    df = validate_fk(df, "observatory_b", set_obs, source="bridge_commune_obs")
    return df[COLUMNS]


def load_bridge(df: pd.DataFrame, conn):
    cur = conn.cursor()
    try:
        cur.execute("TRUNCATE TABLE silver.bridge_commune_observatoire CASCADE")
        cur.executemany("""
            INSERT INTO silver.bridge_commune_observatoire (code_insee, observatory_b)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, df.itertuples(index=False, name=None))
        conn.commit()
        print(f"[BRIDGE_COMMUNE_OBS] {len(df)} relations insérées")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()


def run_silver_bridge_commune_observatoire():
    engine = get_engine()
    conn = get_conn()

    print("[BRIDGE_COMMUNE_OBS] Chargement des sets valides...")
    set_commune, set_obs = load_valid_sets(engine)
    print(f"[BRIDGE_COMMUNE_OBS] {len(set_commune)} communes, {len(set_obs)} observatoires")

    print("[BRIDGE_COMMUNE_OBS] Extraction...")
    df = extract_bridge(engine, conn)

    print("[BRIDGE_COMMUNE_OBS] Transformation + validation FK...")
    df = transform_bridge(df, set_commune, set_obs)
    print(f"[BRIDGE_COMMUNE_OBS] {len(df)} relations valides")

    print("[BRIDGE_COMMUNE_OBS] Chargement...")
    load_bridge(df, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_bridge_commune_observatoire()
