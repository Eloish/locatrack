import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine
import yaml

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path, "r") as f:
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

cur = conn.cursor()

# =========================
# EXTRACTION
# =========================
annees_loyers = [2014, 2015, 2016, 2020, 2021, 2022, 2023, 2024, 2025]

all_agglo = []

for annee in annees_loyers:
    print(f"📥 Lecture staging.loyers_{annee}...")

    query = f"""
        SELECT DISTINCT agglomeration
        FROM staging.loyers_{annee}
        WHERE agglomeration IS NOT NULL
    """

    df = pd.read_sql(query, engine)
    all_agglo.append(df)

# =========================
# VALIDATION
# =========================
if not all_agglo:
    raise SystemExit("❌ Aucune donnée trouvée dans staging.loyers_*")

df_agglo = pd.concat(all_agglo, ignore_index=True)

# =========================
# TRANSFORMATION
# =========================
df_agglo = (
    df_agglo
    .dropna()
    .drop_duplicates()
    .rename(columns={"agglomeration": "nom_agglomeration"})
)

print(f"📊 Agglomérations uniques : {len(df_agglo)}")
print(df_agglo.head(10))

# =========================
# LOAD (BATCH INSERT OPTIMISÉ)
# =========================
values = [(row,) for row in df_agglo["nom_agglomeration"]]

insert_query = """
    INSERT INTO silver.dim_agglomeration (nom_agglomeration)
    VALUES %s
    ON CONFLICT (nom_agglomeration) DO NOTHING
"""

execute_values(cur, insert_query, values)

conn.commit()

# =========================
# CLEANUP
# =========================
cur.close()
conn.close()

print("✅ dim_agglomeration remplie avec succès !")