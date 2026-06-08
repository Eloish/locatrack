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
    host=db["host"],
    port=db["port"],
    dbname=db["name"],
    user=db["user"],
    password=db["password"],
)

cur = conn.cursor()

# =====================
# LOAD ALL LOYERS YEARS
# =====================
annees = [2020, 2021, 2022, 2023, 2024, 2025]

dfs = []

for annee in annees:
    table = f"staging.loyers_{annee}"
    print(f"📥 {table}")

    try:
        df = pd.read_sql(f"""
            SELECT DISTINCT
                TRIM("Observatory") AS observatory_b,
                TRIM(agglomeration) AS nom_agglomeration
            FROM {table}
            WHERE "Observatory" IS NOT NULL
              AND agglomeration IS NOT NULL
        """, engine)

        dfs.append(df)

    except Exception as e:
        print(f"⚠️ skip {table}: {e}")

# =====================
# CONCAT
# =====================
df = pd.concat(dfs, ignore_index=True)

# =====================
# CLEANING IMPORTANT
# =====================
df["observatory_b"] = df["observatory_b"].astype(str).str.strip()
df["nom_agglomeration"] = df["nom_agglomeration"].astype(str).str.strip()

df = df.dropna()
df = df.drop_duplicates()

# 🔥 optional : éviter valeurs cassées encoding
df = df[
    (df["observatory_b"].str.len() > 0) &
    (df["nom_agglomeration"].str.len() > 0)
]

print(f"📊 BRIDGE FINAL: {len(df)} lignes")

# =====================
# INSERT
# =====================
sql = """
INSERT INTO silver.bridge_observatoire_agglomeration (
    observatory_b,
    nom_agglomeration
)
VALUES (%s, %s)
ON CONFLICT DO NOTHING;
"""

cur.executemany(sql, list(df.itertuples(index=False, name=None)))

conn.commit()
cur.close()
conn.close()

print("✅ bridge_observatoire_agglomeration OK")