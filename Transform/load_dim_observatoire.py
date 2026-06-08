import pandas as pd
from sqlalchemy import create_engine
import yaml
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)

annees = [2014, 2015, 2016, 2020, 2021, 2022, 2023, 2024, 2025]

dfs = []

for annee in annees:
    df = pd.read_sql(f"""
        SELECT DISTINCT
            TRIM(UPPER("Observatory")) AS observatory_b
        FROM staging.loyers_{annee}
        WHERE "Observatory" IS NOT NULL
    """, engine)

    dfs.append(df)

dim_obs = pd.concat(dfs, ignore_index=True)

# CLEAN FINAL (ULTRA IMPORTANT)
dim_obs["observatory_b"] = (
    dim_obs["observatory_b"]
    .str.replace("\u00A0", "", regex=False)
    .str.replace(".0", "", regex=False)
    .str.strip()
    .str.upper()
)

dim_obs = dim_obs.drop_duplicates()

print("📊 DIM OBS FINAL:", len(dim_obs))

# LOAD DIM CLEAN RESET
conn = engine.raw_connection()
cur = conn.cursor()

cur.execute("TRUNCATE silver.dim_observatoire CASCADE")

from io import StringIO
buffer = StringIO()

dim_obs.to_csv(buffer, index=False, header=False)
buffer.seek(0)

cur.copy_expert("""
    COPY silver.dim_observatoire (observatory_b)
    FROM STDIN WITH (FORMAT CSV, NULL '')
""", buffer)

conn.commit()
cur.close()
conn.close()

print("✅ dim_observatoire RECONSTRUITE")