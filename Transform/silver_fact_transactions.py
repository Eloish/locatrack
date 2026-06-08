import os
import pandas as pd
import psycopg2
from io import StringIO
from sqlalchemy import create_engine
import yaml

# ==================================================
# CONFIG
# ==================================================
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
    password=db["password"]
)

# ==================================================
# NORMALISATION INSEE (SAFE)
# ==================================================
def normaliser_insee(dep, com):
    dep = str(dep).strip()
    com = str(com).strip().zfill(3)

    if dep in ["2A", "2B"]:
        return dep + com

    return dep.zfill(2) + com


def nettoyer_float(series):
    if series.dtype == object:
        return (
            series.astype(str)
            .str.replace(",", ".")
            .pipe(pd.to_numeric, errors="coerce")
        )
    return pd.to_numeric(series, errors="coerce")


# ==================================================
# 1. LOAD DVF
# ==================================================
annees_dvf = [2021, 2022, 2023, 2024, 2025]
rows = []

for annee in annees_dvf:
    print(f"Traitement DVF {annee}...")

    df = pd.read_sql(f"""
        SELECT
            "Code_commune" as com,
            "Code_departement" as dep,
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

    # INSEE
    df["code_insee"] = df.apply(
        lambda x: normaliser_insee(x["dep"], x["com"]),
        axis=1
    )

    # conversions
    df["valeur_fonciere"] = nettoyer_float(df["valeur_fonciere"])
    df["surface_bati"] = nettoyer_float(df["surface_bati"])
    df["surface_terrain"] = nettoyer_float(df["surface_terrain"])
    df["nombre_pieces"] = nettoyer_float(df["nombre_pieces"])
    df["annee"] = df["annee"].astype("Int64")

    df["prix_m2"] = df["valeur_fonciere"] / df["surface_bati"]

    df = df[[
        "code_insee",
        "annee",
        "type_local",
        "nature_mutation",
        "valeur_fonciere",
        "surface_bati",
        "surface_terrain",
        "nombre_pieces",
        "prix_m2",
        "nature_culture"
    ]]

    rows.append(df)
    print(f"  → {len(df)} lignes")

df_final = pd.concat(rows, ignore_index=True)

# ==================================================
# 2. FK SAFE FILTER (IMPORTANT 🔥)
# ==================================================
dim_commune = pd.read_sql("""
    SELECT code_insee
    FROM silver.dim_commune
""", engine)

valid_insee = set(
    dim_commune["code_insee"]
    .astype(str)
    .str.strip()
)

df_final["code_insee"] = df_final["code_insee"].astype(str).str.strip()

before = len(df_final)
df_final = df_final[df_final["code_insee"].isin(valid_insee)]
after = len(df_final)

print(f"📊 FK FILTER: {before} → {after}")

# ==================================================
# 3. FINAL CLEAN (ANTI COPY ERROR)
# ==================================================
expected_cols = [
    "code_insee",
    "annee",
    "type_local",
    "nature_mutation",
    "valeur_fonciere",
    "surface_bati",
    "surface_terrain",
    "nombre_pieces",
    "prix_m2",
    "nature_culture"
]

df_final = df_final[expected_cols]

# ==================================================
# 4. LOAD (COPY SAFE)
# ==================================================
print("Chargement dans silver.fact_transactions...")

cur = conn.cursor()

cur.execute("TRUNCATE TABLE silver.fact_transactions CASCADE")

buffer = StringIO()
df_final.to_csv(buffer, index=False, header=False, na_rep="")
buffer.seek(0)

cur.copy_expert(f"""
COPY silver.fact_transactions (
    {", ".join(expected_cols)}
)

FROM STDIN WITH (FORMAT CSV, NULL '')
""", buffer)

conn.commit()
cur.close()
conn.close()

print(f"✅ FACT_TRANSACTIONS OK — {len(df_final)} lignes insérées")