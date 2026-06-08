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

# Détecter automatiquement les années DVF depuis le dossier bronze
print("Détection des années DVF disponibles...")
dvf_dir = os.path.join(BASE_DIR, "data", "bronze", "dvf")
annees = []
if os.path.exists(dvf_dir):
    for entry in os.listdir(dvf_dir):
        if entry.startswith("annee="):
            try:
                annees.append(int(entry.split("=", 1)[1]))
            except ValueError:
                continue

annees = sorted(annees)
if not annees:
    raise SystemExit("Aucune année DVF trouvée dans data/bronze/dvf. Vérifie les dossiers.")

print(f"Années DVF détectées : {annees}")

# Rassembler tous les types uniques sur toutes les années DVF
all_types = set()
for annee in annees:
    print(f"Lecture des types depuis staging.dvf_{annee}...")
    df_types = pd.read_sql(f"""
        SELECT DISTINCT "Type_local" as type_bien
        FROM staging.dvf_{annee}
        WHERE "Type_local" IS NOT NULL
    """, engine)
    all_types.update(df_types["type_bien"].dropna().astype(str).tolist())

types = sorted(all_types)
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