import os
import pandas as pd
import psycopg2
from io import StringIO
from sqlalchemy import create_engine
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

def nettoyer_float(series):
    if series.dtype == object:
        return (
            series.astype(str)
            .str.replace(",", ".")
            .pipe(pd.to_numeric, errors="coerce")
        )
    return pd.to_numeric(series, errors="coerce")

annees_loyers = [2014, 2015, 2016, 2020, 2021, 2022, 2023, 2024, 2025]
rows = []

for annee in annees_loyers:
    print(f"Traitement loyers {annee}...")

    df_loyers = pd.read_sql(f"""
        SELECT 
            "agglomeration" as nom_agglomeration,
            "Data_year" as annee,
            "Type_habitat" as type_habitat,
            "nombre_pieces_homogene" as nombre_pieces,
            "loyer_mensuel_median",
            "loyer_median" as loyer_median_m2,
            "nombre_observations"
        FROM staging.loyers_{annee}
        WHERE "loyer_mensuel_median" IS NOT NULL
    """, engine)

    # Convertir colonnes numériques
    for col in ["loyer_mensuel_median", "loyer_median_m2", "nombre_observations"]:
        df_loyers[col] = nettoyer_float(df_loyers[col])

    # Garder seulement les colonnes nécessaires
    df_loyers = df_loyers[[
        "nom_agglomeration", "annee", "type_habitat", "nombre_pieces",
        "loyer_mensuel_median", "loyer_median_m2", "nombre_observations"
    ]].dropna(subset=["nom_agglomeration"])

    rows.append(df_loyers)
    print(f"  → {len(df_loyers)} lignes")

df_final = pd.concat(rows, ignore_index=True)
print(f"\nTotal lignes : {len(df_final)}")

# Charger dans fact_loyers
print("Chargement dans silver.fact_loyers...")
cur = conn.cursor()
buffer = StringIO()
df_final.to_csv(buffer, index=False, header=False, na_rep="")
buffer.seek(0)

cur.copy_expert("""
    COPY silver.fact_loyers (
        nom_agglomeration, annee, type_habitat, nombre_pieces,
        loyer_mensuel_median, loyer_median_m2, nombre_observations
    )
    FROM STDIN WITH (FORMAT CSV, NULL '')
""", buffer)

conn.commit()
cur.close()
conn.close()

print(f"✅ fact_loyers remplie — {len(df_final)} lignes !")