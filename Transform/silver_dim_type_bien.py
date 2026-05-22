import os
import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

db = config["database"]
engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)
conn = psycopg2.connect(
    host=db['host'], port=db['port'],
    dbname=db['name'], user=db['user'],
    password=db['password']
)
cur = conn.cursor()

# Détecter automatiquement les types depuis staging DVF
# On prend tous les types distincts présents dans les données
print("Détection des types de biens depuis staging...")
df_types = pd.read_sql("""
    SELECT DISTINCT "Type_local" as type_bien
    FROM staging.dvf_2024
    WHERE "Type_local" IS NOT NULL
""", engine)

types = df_types["type_bien"].tolist()
print(f"Types détectés : {types}")

for type_bien in types:
    cur.execute("""
        INSERT INTO silver.dim_type_bien (type_bien)
        VALUES (%s)
        ON CONFLICT (type_bien) DO NOTHING
    """, (type_bien,))

conn.commit()
cur.close()
conn.close()

print(f"✅ dim_type_bien remplie — {len(types)} types !")