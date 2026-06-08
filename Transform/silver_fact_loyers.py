import os
import pandas as pd
from sqlalchemy import create_engine
import yaml
import re
import unicodedata
from io import StringIO

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)

# =========================
# PARAMS
# =========================
annees_loyers = [2014, 2015, 2016, 2020, 2021, 2022, 2023, 2024, 2025]

dfs = []

# =========================
# EXTRACTION
# =========================
for annee in annees_loyers:
    print(f"📥 staging.loyers_{annee}")

    df = pd.read_sql(
        f"""
        SELECT
            TRIM(UPPER("Observatory")) AS observatory_b,
            "Data_year" AS annee,
            "Type_habitat" AS type_habitat,
            "nombre_pieces_homogene" AS nombre_pieces,
            "loyer_mensuel_median",
            "loyer_median" AS loyer_median_m2,
            "nombre_observations"
        FROM staging.loyers_{annee}
        WHERE "Observatory" IS NOT NULL
        """,
        engine
    )

    dfs.append(df)

# =========================
# CONCAT
# =========================
df = pd.concat(dfs, ignore_index=True)

# =========================
# CLEAN
# =========================
def clean_obs(x):
    if pd.isna(x):
        return None

    x = str(x)
    x = x.replace("\u00A0", " ")
    x = unicodedata.normalize("NFKC", x)
    x = re.sub(r"\.0$", "", x)
    x = re.sub(r"\s+", "", x)

    return x.upper().strip()

df["observatory_b"] = df["observatory_b"].apply(clean_obs)

# =========================
# NUMERIC
# =========================
for col in [
    "loyer_mensuel_median",
    "loyer_median_m2",
    "nombre_observations"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# =========================
# DROP INVALID
# =========================
df = df.dropna(subset=["observatory_b", "annee"])

# =========================
# DEBUG
# =========================
print("\n📊 STATISTIQUES")
print("Total lignes :", len(df))
print("Observatoires uniques :", df["observatory_b"].nunique())

# =========================
# FACT
# =========================
df_final = df[
    [
        "observatory_b",
        "annee",
        "type_habitat",
        "nombre_pieces",
        "loyer_mensuel_median",
        "loyer_median_m2",
        "nombre_observations"
    ]
]

print("\n📦 Lignes finales fact :", len(df_final))

# =========================
# LOAD
# =========================
raw_conn = engine.raw_connection()
cur = raw_conn.cursor()

try:
    # facultatif : vider la table avant chargement
    cur.execute("TRUNCATE TABLE silver.fact_loyers")

    output = StringIO()
    df_final.to_csv(output, index=False, header=False)
    output.seek(0)

    cur.copy_expert(
        """
        COPY silver.fact_loyers (
            observatory_b,
            annee,
            type_habitat,
            nombre_pieces,
            loyer_mensuel_median,
            loyer_median_m2,
            nombre_observations
        )
        FROM STDIN
        WITH (
            FORMAT CSV,
            NULL ''
        )
        """,
        output
    )

    raw_conn.commit()

    # Vérification
    cur.execute("""
        SELECT COUNT(*)
        FROM silver.fact_loyers
    """)

    nb = cur.fetchone()[0]

    print(f"\n✅ fact_loyers chargée")
    print(f"📊 Nombre de lignes dans PostgreSQL : {nb}")

except Exception as e:
    raw_conn.rollback()
    print(f"\n❌ ERREUR : {e}")

finally:
    cur.close()
    raw_conn.close()