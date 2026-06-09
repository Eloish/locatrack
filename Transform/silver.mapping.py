import pandas as pd
from sqlalchemy import create_engine, text
import yaml
import os
import re
import unicodedata

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@"
    f"{db['host']}:{db['port']}/{db['name']}"
)

# ============================================================
# CLEANING
# ============================================================

def clean_text(x):

    if pd.isna(x):
        return None

    x = str(x)

    try:
        x = x.encode("latin1").decode("utf-8")
    except:
        pass

    x = unicodedata.normalize("NFKC", x)

    x = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', x)

    x = re.sub(r'\s+', ' ', x)

    return x.strip()


def trouver_colonne(df, candidats):

    cols_upper = {c.upper(): c for c in df.columns}

    for candidat in candidats:

        if candidat.upper() in cols_upper:
            return cols_upper[candidat.upper()]

    return None

# ============================================================
# TABLES STAGING
# ============================================================

print("🚀 Construction du mapping Silver")

with engine.connect() as conn:

    tables = pd.read_sql(
        text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname='staging'
            AND tablename LIKE 'zonage_%'
            ORDER BY tablename
        """),
        conn
    )

print(f"📊 Tables trouvées : {len(tables)}")

rows = []

# ============================================================
# LECTURE DES TABLES
# ============================================================

for table in tables["tablename"]:

    print(f"📥 {table}")

    with engine.connect() as conn:

        df = pd.read_sql(
            text(f'SELECT * FROM staging."{table}"'),
            conn
        )

    if df.empty:
        continue

    col_insee = trouver_colonne(df, [
        "INSEE",
        "CODE_INSEE",
        "INSEE_COM",
        "COD_COM",
        "L6A",
        "COMMUNE"
    ])

    col_commune = trouver_colonne(df, [
        "LIB_COM",
        "LIBCOM",
        "NOM_COM",
        "NOM_COMMUNE"
    ])

    col_zone = trouver_colonne(df, [
        "ZONE"
    ])

    col_libzone = trouver_colonne(df, [
        "LIB_ZONE",
        "LIB_IRIS"
    ])

    if col_insee is None:
        print(f"⚠ colonne INSEE absente : {table}")
        continue

    df_out = pd.DataFrame()

    df_out["code_insee"] = df[col_insee]

    df_out["nom_commune"] = (
        df[col_commune]
        if col_commune else None
    )

    df_out["zone"] = (
        df[col_zone]
        if col_zone else None
    )

    df_out["lib_zone"] = (
        df[col_libzone]
        if col_libzone else None
    )

    if "observatory_b" in df.columns:
        df_out["observatory_b"] = df["observatory_b"]
    else:
        df_out["observatory_b"] = table.replace("zonage_", "").upper()

    rows.append(df_out)

# ============================================================
# CONCAT
# ============================================================

if not rows:
    raise Exception("Aucune donnée récupérée")

df = pd.concat(rows, ignore_index=True)

print(f"\n📊 Lignes brutes : {len(df)}")

# ============================================================
# CLEAN
# ============================================================

for col in df.columns:
    df[col] = df[col].apply(clean_text)

df["code_insee"] = (
    df["code_insee"]
    .astype(str)
    .str.strip()
    .str.zfill(5)
)

df["observatory_b"] = (
    df["observatory_b"]
    .astype(str)
    .str.upper()
    .str.strip()
)

df = df.drop_duplicates(
    subset=["code_insee", "observatory_b"]
)

print(f"🧹 Après nettoyage : {len(df)}")

# ============================================================
# TABLE INTERMEDIAIRE
# ============================================================

with engine.begin() as conn:

    conn.execute(text("""
        DROP TABLE IF EXISTS silver.mapping_communes;
    """))

df.to_sql(
    "mapping_communes",
    con=engine,
    schema="silver",
    if_exists="replace",
    index=False
)

print("✅ silver.mapping_communes")

# ============================================================
# DIM OBSERVATOIRE
# ============================================================

dim_obs = (
    df[["observatory_b"]]
    .drop_duplicates()
)

with engine.begin() as conn:

    conn.execute(text("""
        TRUNCATE TABLE silver.dim_observatoire CASCADE;
    """))

dim_obs.to_sql(
    "dim_observatoire",
    con=engine,
    schema="silver",
    if_exists="append",
    index=False
)

print("✅ dim_observatoire")

# ============================================================
# DIM COMMUNE
# ============================================================

dim_commune = (
    df[
        ["code_insee", "nom_commune"]
    ]
    .drop_duplicates(subset=["code_insee"])
)

with engine.begin() as conn:

    conn.execute(text("""
        TRUNCATE TABLE silver.dim_commune CASCADE;
    """))

dim_commune.to_sql(
    "dim_commune",
    con=engine,
    schema="silver",
    if_exists="append",
    index=False
)

print("✅ dim_commune")

# ============================================================
# BRIDGE COMMUNE OBSERVATOIRE
# ============================================================

bridge = (
    df[
        ["code_insee", "observatory_b"]
    ]
    .drop_duplicates()
)

with engine.begin() as conn:

    conn.execute(text("""
        TRUNCATE TABLE silver.bridge_commune_observatoire;
    """))

bridge.to_sql(
    "bridge_commune_observatoire",
    con=engine,
    schema="silver",
    if_exists="append",
    index=False
)

print("✅ bridge_commune_observatoire")

print("\n🎉 Mapping Silver terminé")