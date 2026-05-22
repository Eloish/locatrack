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

annees_dvf = [2021, 2022, 2023, 2024, 2025]
rows = []

for annee in annees_dvf:
    print(f"Traitement DVF {annee}...")

    df_dvf = pd.read_sql(f"""
        SELECT
            LPAD("Code_commune"::text, 3, '0') as code_commune,
            "Code_departement" as code_departement,
            EXTRACT(YEAR FROM TO_DATE("Date_mutation", 'DD/MM/YYYY')) as annee,
            "Nature_mutation" as nature_mutation,
            "Type_local" as type_local,
            REPLACE("Valeur_fonciere", ',', '.')::FLOAT as valeur_fonciere,
            "Surface_reelle_bati" as surface_bati,
            "Surface_terrain" as surface_terrain,
            "Nombre_pieces_principales" as nombre_pieces,
            "Nature_culture" as nature_culture
        FROM staging.dvf_{annee}
        WHERE "Nature_mutation" = 'Vente'
        AND "Type_local" IS NOT NULL
        AND "Surface_reelle_bati" > 0
        AND "Valeur_fonciere" IS NOT NULL
    """, engine)

    # Construire code INSEE
    df_dvf["code_departement"] = df_dvf["code_departement"].astype(str).str.zfill(2)
    df_dvf["code_commune"] = df_dvf["code_commune"].astype(str).str.zfill(3)
    df_dvf["code_insee"] = df_dvf["code_departement"] + df_dvf["code_commune"]

    # Convertir types
    df_dvf["valeur_fonciere"] = nettoyer_float(df_dvf["valeur_fonciere"])
    df_dvf["surface_bati"] = nettoyer_float(df_dvf["surface_bati"])
    df_dvf["surface_terrain"] = nettoyer_float(df_dvf["surface_terrain"])
    df_dvf["nombre_pieces"] = nettoyer_float(df_dvf["nombre_pieces"])
    df_dvf["annee"] = df_dvf["annee"].astype("Int64")

    # Calculer prix au m²
    df_dvf["prix_m2"] = df_dvf["valeur_fonciere"] / df_dvf["surface_bati"]

    # Filtrer aberrations
    seuil_bas = 500
    seuil_haut = 13731
    df_dvf = df_dvf[
        (df_dvf["prix_m2"] >= seuil_bas) &
        (df_dvf["prix_m2"] <= seuil_haut)
    ]

    # Garder colonnes finales
    df_dvf = df_dvf[[
        "code_insee", "annee", "type_local", "nature_mutation",
        "valeur_fonciere", "surface_bati", "surface_terrain",
        "nombre_pieces", "prix_m2", "nature_culture"
    ]].dropna(subset=["code_insee", "annee"])

    rows.append(df_dvf)
    print(f"  → {len(df_dvf)} transactions")

df_final = pd.concat(rows, ignore_index=True)
print(f"\nTotal lignes : {len(df_final)}")

# Charger dans fact_transactions
print("Chargement dans silver.fact_transactions...")
cur = conn.cursor()
buffer = StringIO()
df_final.to_csv(buffer, index=False, header=False, na_rep="")
buffer.seek(0)

cur.copy_expert("""
    COPY silver.fact_transactions (
        code_insee, annee, type_local, nature_mutation,
        valeur_fonciere, surface_bati, surface_terrain,
        nombre_pieces, prix_m2, nature_culture
    )
    FROM STDIN WITH (FORMAT CSV, NULL '')
""", buffer)

conn.commit()
cur.close()
conn.close()

print(f"✅ fact_transactions remplie — {len(df_final)} lignes !")
