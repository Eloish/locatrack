import os
import pandas as pd
import psycopg2
from io import StringIO
from sqlalchemy import create_engine
import yaml

# ==================================================
# CONFIG
# ==================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)

conn = psycopg2.connect(
    host=db["host"],
    port=db["port"],
    dbname=db["name"],
    user=db["user"],
    password=db["password"]
)

# ==================================================
# CONFIG SCHÉMA (ULTRA IMPORTANT)
# ==================================================
SCHEMA = [
    "code_insee",
    "nom_commune",
    "code_postal",
    "code_departement",
    "region"
]

# ==================================================
# NORMALISATION INSEE
# ==================================================
def normaliser_insee(dep, com):
    dep = str(dep).strip()

    if dep in ["2A", "2B"]:
        return dep + str(com).zfill(3)

    return str(dep).zfill(2) + str(com).zfill(3)

# ==================================================
# SAFE CLEAN FUNCTION
# ==================================================
def clean_df(df):
    # garder uniquement colonnes existantes utiles
    for col in SCHEMA:
        if col not in df.columns:
            df[col] = None

    df = df[SCHEMA]

    # nettoyage string
    for c in ["code_insee", "nom_commune", "code_postal", "code_departement", "region"]:
        df[c] = df[c].astype(str).replace("nan", None)

    # INSEE valid
    df = df[df["code_insee"].notna()]
    df["code_insee"] = df["code_insee"].str.strip()
    df = df[df["code_insee"].str.len().between(5, 6)]

    # dedup
    df = df.drop_duplicates(subset=["code_insee"], keep="first")

    return df

# ==================================================
# PIPELINE
# ==================================================
print("🚀 BUILD DIM_COMMUNE ROBUST PIPELINE")

frames = []

# =====================
# 1. STAGING COMMUNES
# =====================
try:
    df = pd.read_sql("SELECT * FROM staging.communes", engine)

    df = df.rename(columns={
        "nom_standard": "nom_commune",
        "dep_code": "code_departement"
    })

    frames.append(df)
    print(f"📥 staging.communes: {len(df)}")

except Exception as e:
    print("⚠️ staging.communes:", e)

# =====================
# 2. DVF
# =====================
for year in range(2021, 2026):
    try:
        df = pd.read_sql(f"""
            SELECT DISTINCT
                "Code_departement",
                "Code_commune",
                "Commune",
                "Code_postal"
            FROM staging.dvf_{year}
        """, engine)

        df["code_insee"] = df.apply(
            lambda x: normaliser_insee(x["Code_departement"], x["Code_commune"]),
            axis=1
        )

        df = df.rename(columns={
            "Commune": "nom_commune",
            "Code_postal": "code_postal",
            "Code_departement": "code_departement"
        })

        df["region"] = None

        frames.append(df)

        print(f"📥 DVF {year}: {len(df)}")

    except Exception as e:
        print(f"⚠️ DVF {year}: {e}")

# =====================
# 3. INSEE SAFE LOOP
# =====================
for year in range(2017, 2026):
    table = f"staging.insee_{year}"

    try:
        df = pd.read_sql(f"""
            SELECT DISTINCT
                "CODGEO" AS code_insee,
                "LIBGEO" AS nom_commune
            FROM {table}
        """, engine)

        df["code_postal"] = None
        df["code_departement"] = None
        df["region"] = None

        frames.append(df)

        print(f"📥 INSEE {year}: {len(df)}")

    except Exception:
        continue

# =====================
# 4. MAPPING (OPTIONNEL ENRICHISSEMENT)
# =====================
try:
    mapping = pd.read_sql("""
        SELECT code_insee,
               nom_commune,
               nom_agglomeration
        FROM ref.mapping_communes
    """, engine)

    mapping = mapping[["code_insee", "nom_commune"]]
    frames.append(mapping)

    print(f"📥 mapping: {len(mapping)}")

except Exception as e:
    print("⚠️ mapping:", e)

# ==================================================
# CONCAT + CLEAN GLOBAL
# ==================================================
df = pd.concat(frames, ignore_index=True)

df = clean_df(df)

# ==================================================
# NORMALISATION POST-CLEAN
# ==================================================
df["code_postal"] = pd.to_numeric(df["code_postal"], errors="coerce")
df["code_postal"] = (
    df["code_postal"]
    .fillna(0)
    .astype(int)
    .astype(str)
    .str.zfill(5)
)

df.loc[df["code_postal"] == "00000", "code_postal"] = None

# ==================================================
# FINAL SAFETY CHECK (CRITIQUE)
# ==================================================
assert list(df.columns) == SCHEMA, "❌ Schema mismatch BEFORE COPY"

print(f"📊 FINAL DIM_COMMUNE: {len(df)} lignes")
print("📦 Colonnes:", df.columns.tolist())

# ==================================================
# LOAD SAFE COPY
# ==================================================
cur = conn.cursor()

cur.execute("TRUNCATE TABLE silver.dim_commune CASCADE")

buffer = StringIO()
df.to_csv(buffer, index=False, header=False, na_rep="")
buffer.seek(0)

cur.copy_expert(f"""
COPY silver.dim_commune (
    {", ".join(SCHEMA)}
)
FROM STDIN WITH (FORMAT CSV, NULL '')
""", buffer)

conn.commit()
cur.close()
conn.close()

print("✅ DIM_COMMUNE ROBUST PIPELINE OK")