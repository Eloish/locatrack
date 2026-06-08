import pandas as pd
from sqlalchemy import create_engine
import psycopg2
import yaml
import os

# =====================
# CONFIG
# =====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)

print("🚀 BUILD bridge_commune_observatoire CLEAN")

# =====================
# 1. LOAD DIMENSIONS VALIDES
# =====================

dim_commune = pd.read_sql("""
    SELECT code_insee
    FROM silver.dim_commune
""", engine)

dim_obs = pd.read_sql("""
    SELECT observatory_b
    FROM silver.dim_observatoire
""", engine)

dim_commune["code_insee"] = dim_commune["code_insee"].astype(str).str.strip()
dim_obs["observatory_b"] = dim_obs["observatory_b"].astype(str).str.strip()

set_commune = set(dim_commune["code_insee"])
set_obs = set(dim_obs["observatory_b"])

print(f"📊 communes valides: {len(set_commune)}")
print(f"📊 observatoires valides: {len(set_obs)}")

# =====================
# 2. LOAD MAPPING (source vérité)
# =====================
mapping = pd.read_sql("""
    SELECT code_insee,
           observatory_b,
           nom_agglomeration
    FROM ref.mapping_communes
""", engine)

# nettoyage agressif
mapping["code_insee"] = mapping["code_insee"].astype(str).str.strip()
mapping["observatory_b"] = mapping["observatory_b"].astype(str).str.strip()

# =====================
# 3. FILTER VALID KEYS
# =====================

df_bridge = mapping[
    mapping["code_insee"].isin(set_commune) &
    mapping["observatory_b"].isin(set_obs)
].copy()

df_bridge = df_bridge[["code_insee", "observatory_b"]].drop_duplicates()

print(f"📊 relations valides: {len(df_bridge)}")

# =====================
# 4. INSERT POSTGRES
# =====================
conn = psycopg2.connect(
    host=db["host"],
    port=db["port"],
    dbname=db["name"],
    user=db["user"],
    password=db["password"]
)

cur = conn.cursor()

cur.execute("TRUNCATE TABLE silver.bridge_commune_observatoire CASCADE;")

sql = """
INSERT INTO silver.bridge_commune_observatoire
(code_insee, observatory_b)
VALUES (%s, %s)
ON CONFLICT DO NOTHING;
"""

cur.executemany(sql, df_bridge.itertuples(index=False, name=None))

conn.commit()
cur.close()
conn.close()

print("✅ bridge_commune_observatoire OK")