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

# Colonnes revenu par année INSEE
col_revenu_par_annee = {
    2017: "Q217",
    2018: "Q218",
    2019: "Q219",
    2020: "Q220",
    2021: "Q221",
}

rows = []

for annee, col_revenu in col_revenu_par_annee.items():
    print(f"Traitement INSEE {annee} ({col_revenu})...")

    df_insee = pd.read_sql(f"""
        SELECT 
            "CODGEO" as code_insee,
            "{col_revenu}"::text as revenu_median
        FROM staging.insee_{annee}
        WHERE "{col_revenu}"::text != 's'
        AND "{col_revenu}" IS NOT NULL
    """, engine)

    # Convertir en float
    df_insee["revenu_median"] = nettoyer_float(df_insee["revenu_median"])
    
    # Calculer revenu mensuel
    df_insee["revenu_mensuel"] = df_insee["revenu_median"] / 12
    
    # Ajouter l'année
    df_insee["annee"] = annee

    # Supprimer les nulls
    df_insee = df_insee.dropna(subset=["revenu_median"])

    rows.append(df_insee[["code_insee", "annee", "revenu_median", "revenu_mensuel"]])
    print(f"  → {len(df_insee)} communes")

df_final = pd.concat(rows, ignore_index=True)
print(f"\nTotal lignes : {len(df_final)}")

# Charger dans fact_revenus
print("Chargement dans silver.fact_revenus...")
cur = conn.cursor()
buffer = StringIO()
df_final.to_csv(buffer, index=False, header=False, na_rep="")
buffer.seek(0)

cur.copy_expert("""
    COPY silver.fact_revenus (
        code_insee, annee, revenu_median, revenu_mensuel
    )
    FROM STDIN WITH (FORMAT CSV, NULL '')
""", buffer)

conn.commit()
cur.close()
conn.close()

print(f"✅ fact_revenus remplie — {len(df_final)} lignes !")