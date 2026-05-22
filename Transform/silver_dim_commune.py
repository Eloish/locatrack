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

# Utiliser SQLAlchemy pour pd.read_sql
engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)

conn = psycopg2.connect(
    host=db['host'], port=db['port'],
    dbname=db['name'], user=db['user'],
    password=db['password']
)

# Charger staging.communes
print("Chargement staging.communes...")
df_communes = pd.read_sql("SELECT * FROM staging.communes", engine)

# Charger le mapping observatory → communes
print("Chargement mapping...")
df_mapping = pd.read_csv(
    os.path.join(BASE_DIR, "data/mapping_observatory_communes.csv")
)

# Charger dim_agglomeration pour avoir le lien observatory_b → nom_agglomeration
print("Chargement dim_agglomeration...")
df_agglo = pd.read_sql(
    "SELECT nom_agglomeration, observatory_b FROM silver.dim_agglomeration",
    engine
)

# Joindre mapping avec agglomeration pour avoir nom_agglomeration par commune
df_mapping = df_mapping.merge(
    df_agglo,
    on="observatory_b",
    how="left"
)

print(f"Communes dans staging    : {len(df_communes)}")
print(f"Communes dans mapping    : {df_mapping['code_insee'].nunique()}")

# Joindre staging.communes avec mapping
df_final = df_communes.merge(
    df_mapping[["code_insee", "nom_agglomeration"]].drop_duplicates("code_insee"),
    on="code_insee",
    how="left"
)

print(f"Communes après jointure  : {len(df_final)}")
print(f"Avec agglomération       : {df_final['nom_agglomeration'].notna().sum()}")
print(f"Sans agglomération       : {df_final['nom_agglomeration'].isna().sum()}")

# Garder seulement les communes avec une agglomération
df_final = df_final[df_final["nom_agglomeration"].notna()].copy()
print(f"Communes filtrées        : {len(df_final)}")

# Préparer les colonnes
df_insert = df_final[[
    "code_insee", "nom_standard", "code_postal",
    "dep_code", "reg_nom", "nom_agglomeration",
    "latitude_mairie", "longitude_mairie", "population"
]].rename(columns={
    "nom_standard": "nom_commune",
    "dep_code": "code_departement",
    "reg_nom": "region",
    "latitude_mairie": "latitude",
    "longitude_mairie": "longitude"
}).copy()

# Convertir types
df_insert["code_insee"] = df_insert["code_insee"].astype(str).str.zfill(5)

# Code postal — correction float → string
df_insert["code_postal"] = (
    pd.to_numeric(df_insert["code_postal"], errors="coerce")
    .astype("Int64")
    .astype(str)
    .str.zfill(5)
    .replace("<NA>", None)
)

# Code departement
df_insert["code_departement"] = df_insert["code_departement"].astype(str).str.zfill(2)

# Population
df_insert["population"] = pd.to_numeric(df_insert["population"], errors="coerce")

print("\nChargement dans silver.dim_commune...")
cur = conn.cursor()

buffer = StringIO()
df_insert.to_csv(buffer, index=False, header=False, na_rep="")
buffer.seek(0)

cur.copy_expert("""
    COPY silver.dim_commune (
        code_insee, nom_commune, code_postal,
        code_departement, region, nom_agglomeration,
        latitude, longitude, population
    )
    FROM STDIN WITH (FORMAT CSV, NULL '')
""", buffer)

conn.commit()
cur.close()
conn.close()

print(f"✅ dim_commune remplie — {len(df_insert)} communes !")