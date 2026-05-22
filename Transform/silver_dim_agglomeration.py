import os
import pandas as pd
import psycopg2
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

db = config["database"]
conn = psycopg2.connect(
    host=db['host'], port=db['port'],
    dbname=db['name'], user=db['user'],
    password=db['password']
)
cur = conn.cursor()

# Charger les loyers 2023 pour avoir le lien observatory_b → nom_agglomeration
df_loyers = pd.read_parquet(
    os.path.join(BASE_DIR, "data/bronze/loyers/annee=2023/loyers_2023.parquet")
)

# Extraire les paires uniques observatory_b / nom_agglomeration
df_agglo = (
    df_loyers[["Observatory", "agglomeration"]]
    .drop_duplicates()
    .rename(columns={
        "Observatory": "observatory_b",
        "agglomeration": "nom_agglomeration"
    })
)

print(f"Agglomérations à insérer : {len(df_agglo)}")
print(df_agglo)

# Insérer dans dim_agglomeration
for _, row in df_agglo.iterrows():
    cur.execute("""
        INSERT INTO silver.dim_agglomeration (nom_agglomeration, observatory_b)
        VALUES (%s, %s)
        ON CONFLICT (nom_agglomeration) DO NOTHING
    """, (row["nom_agglomeration"], row["observatory_b"]))

conn.commit()
cur.close()
conn.close()

print("\n✅ dim_agglomeration remplie !")