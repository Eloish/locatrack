import os
import re
import unicodedata
import pandas as pd
import psycopg2
import numpy as np
from sqlalchemy import create_engine
import yaml

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@"
    f"{db['host']}:{db['port']}/{db['name']}"
)

conn = psycopg2.connect(
    host=db["host"],
    port=db["port"],
    dbname=db["name"],
    user=db["user"],
    password=db["password"]
)

cur = conn.cursor()

# =========================
# CLEAN FUNCTION UNIQUE (IMPORTANT)
# =========================
def clean_text(x):
    if pd.isna(x):
        return None

    x = str(x)

    x = x.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
    x = unicodedata.normalize("NFKC", x)

    x = re.sub(r"\s+", " ", x)

    return x.strip()



# =========================
# LOAD DIM AGGLO
# =========================
dim_aglo = pd.read_sql("""
    SELECT id_agglomeration, nom_agglomeration
    FROM silver.dim_agglomeration
""", engine)

dim_aglo["nom_agglomeration"] = dim_aglo["nom_agglomeration"].apply(clean_text)

# =========================
# LOAD STAGING LOYERS
# =========================
annees = [2014, 2015, 2016, 2020, 2021, 2022, 2023, 2024, 2025]

dfs = []

for annee in annees:
    

    df = pd.read_sql(f"""
        SELECT DISTINCT
            TRIM(UPPER("Observatory")) AS observatory_b,
            TRIM("agglomeration") AS nom_agglomeration
        FROM staging.loyers_{annee}
        WHERE "Observatory" IS NOT NULL
          AND agglomeration IS NOT NULL
    """, engine)

    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

# =========================
# CLEAN STAGING
# =========================
df["observatory_b"] = (
    df["observatory_b"]
    .str.replace("\u00A0", "", regex=False)
    .str.replace(".0", "", regex=False)
    .str.strip()
    .str.upper()
)
df["nom_agglomeration"] = df["nom_agglomeration"].apply(clean_text)

df = df.drop_duplicates()

# =========================
# JOIN (CORE LOGIC)
# =========================
df_bridge = df.merge(dim_aglo, on="nom_agglomeration", how="left")

# =========================
# DEBUG
# =========================
print("\n📊 STATISTIQUES")
print("Total lignes:", len(df_bridge))
print("Observatoires uniques:", df_bridge["observatory_b"].nunique())
print("NULL agglomeration:", df_bridge["id_agglomeration"].isna().sum())

# =========================
# CLEAN FINAL SAFE INSERT
# =========================
df_bridge = df_bridge.replace({np.nan: None})
df_bridge = df_bridge.dropna(subset=["id_agglomeration"])
df_bridge["id_agglomeration"] = df_bridge["id_agglomeration"].astype(int)

# =========================
# INSERT
# =========================
sql = """
INSERT INTO silver.bridge_observatoire_agglomeration (
    observatory_b,
    id_agglomeration
)
VALUES (%s, %s)
ON CONFLICT DO NOTHING;
"""

cur.executemany(
    sql,
    list(df_bridge[["observatory_b", "id_agglomeration"]]
         .itertuples(index=False, name=None))
)

conn.commit()
cur.close()
conn.close()

print("\n✅ Bridge chargé avec succès")