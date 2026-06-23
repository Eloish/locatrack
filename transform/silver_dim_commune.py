import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from utils.config import load_config
from utils.db import get_engine, get_conn
from utils.geography import normaliser_insee
from utils.validators import validate_not_null, validate_columns
from utils.loader import copy_to_postgres

SCHEMA = ["code_insee", "nom_commune", "code_postal", "code_departement", "region", "uu2020", "reg"]
CANDIDATS_INSEE = ["INSEE", "CODE INSEE", "L6A", "CODE_INSEE", "COMMUNE"]
CANDIDATS_LIBCOM = ["LIB_COM", "LIBCOM", "NOM_COM", "COMMUNE"]


def extract_from_communes(engine) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM staging.communes", engine)
    return df.rename(columns={"nom_standard": "nom_commune", "dep_code": "code_departement"})


def extract_from_dvf(engine, years: list) -> pd.DataFrame:
    frames = []
    for year in years:
        try:
            df = pd.read_sql(f"""
                SELECT DISTINCT "Code_departement", "Code_commune", "Commune", "Code_postal"
                FROM staging.dvf_{year}
            """, engine)
            df["code_insee"] = df.apply(lambda x: normaliser_insee(x["Code_departement"], x["Code_commune"]), axis=1)
            df = df.rename(columns={"Commune": "nom_commune", "Code_postal": "code_postal", "Code_departement": "code_departement"})
            df["region"] = None
            frames.append(df)
        except Exception as e:
            print(f"[DIM_COMMUNE] DVF {year} ignoré : {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def extract_from_insee(engine, years: list) -> pd.DataFrame:
    frames = []
    for year in years:
        try:
            df = pd.read_sql(f"""
                SELECT DISTINCT "CODGEO" AS code_insee, "LIBGEO" AS nom_commune
                FROM staging.insee_{year}
            """, engine)
            df["code_postal"] = None
            df["code_departement"] = None
            df["region"] = None
            frames.append(df)
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def extract_from_zonages(engine, conn) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'staging' AND table_name LIKE 'zonage_b%'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    cur.close()

    frames = []
    for table in tables:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'staging' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        cols_clean = {c.strip().upper(): c for c, in cur.fetchall()}
        cur.close()

        col_insee = next((cols_clean[c.upper()] for c in CANDIDATS_INSEE if c.upper() in cols_clean), None)
        if col_insee is None:
            continue
        col_libcom = next((cols_clean[c.upper()] for c in CANDIDATS_LIBCOM
                           if c.upper() in cols_clean and cols_clean[c.upper()] != col_insee), None)
        libcom_select = f'TRIM("{col_libcom}") AS nom_commune' if col_libcom else "NULL AS nom_commune"

        try:
            df = pd.read_sql(f"""
                SELECT DISTINCT TRIM("{col_insee}") AS code_insee, {libcom_select}
                FROM staging.{table} WHERE "{col_insee}" IS NOT NULL
            """, engine)
            df["code_insee"] = df["code_insee"].astype(str).str.strip().str.zfill(5)
            df = df[df["code_insee"].str.match(r'^(\d{5}|2[AB]\d{3})$')]
            df["code_postal"] = None
            df["code_departement"] = None
            df["region"] = None
            frames.append(df)
        except Exception as e:
            print(f"[DIM_COMMUNE] {table} ignoré : {e}")

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def extract_from_ref_geo(engine) -> pd.DataFrame:
    try:
        return pd.read_sql("SELECT code_insee, uu2020, reg FROM staging.communes_geo", engine)
    except Exception as e:
        print(f"[DIM_COMMUNE] staging.communes_geo ignoré : {e}")
        return pd.DataFrame(columns=["code_insee", "uu2020", "reg"])


def transform_dim_commune(frames: list, df_geo: pd.DataFrame) -> pd.DataFrame:
    df = pd.concat(frames, ignore_index=True)

    for col in SCHEMA:
        if col not in df.columns:
            df[col] = None
    df = df[SCHEMA].copy()

    for c in SCHEMA:
        df[c] = df[c].astype(str).replace("nan", None)

    df = validate_not_null(df, ["code_insee"], source="dim_commune")
    df["code_insee"] = df["code_insee"].str.strip()
    df = df[df["code_insee"].str.len().between(5, 6)]
    df = df.drop_duplicates(subset=["code_insee"], keep="first")

    df["code_postal"] = (
        pd.to_numeric(df["code_postal"], errors="coerce")
        .fillna(0).astype(int).astype(str).str.zfill(5)
    )
    df.loc[df["code_postal"] == "00000", "code_postal"] = None

    # Enrichissement uu2020 + reg depuis staging.communes_geo
    if not df_geo.empty:
        df_geo["code_insee"] = df_geo["code_insee"].astype(str).str.strip()
        df = df.merge(df_geo[["code_insee", "uu2020", "reg"]], on="code_insee", how="left", suffixes=("", "_geo"))
        df["uu2020"] = df["uu2020_geo"].combine_first(df["uu2020"])
        df["reg"]    = df["reg_geo"].combine_first(df["reg"])
        df = df.drop(columns=["uu2020_geo", "reg_geo"], errors="ignore")

    assert list(df.columns) == SCHEMA, "Schema mismatch dim_commune"
    return df


def load_dim_commune(df: pd.DataFrame, conn):
    copy_to_postgres(conn, df, schema="silver", table="dim_commune", columns=SCHEMA)


def run_silver_dim_commune():
    config = load_config()
    engine = get_engine()
    conn = get_conn()

    dvf_years = list(config["dvf"]["fichiers"].keys())
    insee_years = list(config["insee"]["fichiers"].keys())

    print("[DIM_COMMUNE] Extraction...")
    frames = []
    try:
        frames.append(extract_from_communes(engine))
    except Exception as e:
        print(f"[DIM_COMMUNE] staging.communes ignoré : {e}")

    frames.append(extract_from_dvf(engine, dvf_years))
    frames.append(extract_from_insee(engine, insee_years))
    frames.append(extract_from_zonages(engine, conn))

    frames = [f for f in frames if not f.empty]
    df_geo = extract_from_ref_geo(engine)

    print("[DIM_COMMUNE] Transformation...")
    df = transform_dim_commune(frames, df_geo)
    print(f"[DIM_COMMUNE] {len(df)} communes")

    print("[DIM_COMMUNE] Chargement...")
    load_dim_commune(df, conn)
    conn.close()


if __name__ == "__main__":
    run_silver_dim_commune()
