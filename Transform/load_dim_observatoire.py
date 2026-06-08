import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import yaml

# =====================
# CONFIG
# =====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)

conn = psycopg2.connect(
    host=db['host'],
    port=db['port'],
    dbname=db['name'],
    user=db['user'],
    password=db['password']
)

cur = conn.cursor()

# =====================
# EXTRACTION OBSERVATOIRES
# =====================
annees = [2020, 2021, 2022, 2023, 2024, 2025]

dfs = []

for annee in annees:
    table = f"staging.loyers_{annee}"
    print(f"📥 Lecture {table}...")

    try:
        df = pd.read_sql(f"""
            SELECT DISTINCT
                TRIM(
                    UPPER(
                        REPLACE(REPLACE("Observatory", CHR(160), ''), '.0', '')
                    )
                ) AS observatory_b
            FROM {table}
            WHERE "Observatory" IS NOT NULL
        """, engine)

        dfs.append(df)

    except Exception as e:
        print(f"⚠️ Erreur {table}: {e}")

# =====================
# CLEAN GLOBAL
# =====================
df_obs = pd.concat(dfs, ignore_index=True)

df_obs["observatory_b"] = (
    df_obs["observatory_b"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# suppression valeurs invalides
df_obs = df_obs[df_obs["observatory_b"] != ""]
df_obs = df_obs[df_obs["observatory_b"].notna()]

# unique propre
df_obs = df_obs.drop_duplicates(subset=["observatory_b"])

print(f"📊 Observatoires uniques finaux: {len(df_obs)}")
print(sorted(df_obs["observatory_b"].tolist()))

# =====================
# (OPTION DEBUG) vérification cohérence
# =====================
df_check = pd.read_sql("""
    SELECT DISTINCT observatory_b
    FROM silver.dim_observatoire
""", engine)

existing = set(df_check["observatory_b"])
incoming = set(df_obs["observatory_b"])

print("➕ Nouveaux:", incoming - existing)
print("➖ Manquants:", existing - incoming)

# =====================
# INSERT SAFE
# =====================
sql = """
INSERT INTO silver.dim_observatoire (observatory_b)
VALUES (%s)
ON CONFLICT (observatory_b) DO NOTHING;
"""

data = [(x,) for x in df_obs["observatory_b"].tolist()]

cur.executemany(sql, data)

conn.commit()
cur.close()
conn.close()

print("✅ dim_observatoire chargée proprement")