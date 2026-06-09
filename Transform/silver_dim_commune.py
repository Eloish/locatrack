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

with open(os.path.join(BASE_DIR, "config.yml")) as f:
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
# CONFIG SCHÉMA
# ==================================================
SCHEMA = [
    "code_insee",
    "nom_commune",
    "code_postal",
    "code_departement",
    "region"
]

# Ordre important : les plus spécifiques en premier
CANDIDATS_INSEE = ["INSEE", "CODE INSEE", "L6A", "CODE_INSEE", "COMMUNE"]
CANDIDATS_LIBCOM = ["LIB_COM", "LIBCOM", "NOM_COM", "COMMUNE"]

# ==================================================
# HELPERS
# ==================================================
def normaliser_insee(dep, com):
    dep = str(dep).strip()
    if dep in ["2A", "2B"]:
        return dep + str(com).zfill(3)
    return str(dep).zfill(2) + str(com).zfill(3)


def clean_df(df):
    for col in SCHEMA:
        if col not in df.columns:
            df[col] = None

    df = df[SCHEMA].copy()

    for c in SCHEMA:
        df[c] = df[c].astype(str).replace("nan", None)

    df = df[df["code_insee"].notna()]
    df["code_insee"] = df["code_insee"].str.strip()
    df = df[df["code_insee"].str.len().between(5, 6)]
    df = df.drop_duplicates(subset=["code_insee"], keep="first")

    return df


# ==================================================
# PIPELINE
# ==================================================
print("🚀 BUILD DIM_COMMUNE")

frames = []

# =====================
# 1. STAGING COMMUNES
# =====================
try:
    df = pd.read_sql("SELECT * FROM staging.communes", engine)
    df = df.rename(columns={
        "nom_standard": "nom_commune",
        "dep_code": "code_departement"
    })
    frames.append(df)
    print(f"📥 staging.communes: {len(df)}")
except Exception as e:
    print(f"⚠️ staging.communes: {e}")

# =====================
# 2. DVF
# =====================
for year in range(2021, 2026):
    try:
        df = pd.read_sql(f"""
            SELECT DISTINCT
                "Code_departement",
                "Code_commune",
                "Commune",
                "Code_postal"
            FROM staging.dvf_{year}
        """, engine)

        df["code_insee"] = df.apply(
            lambda x: normaliser_insee(x["Code_departement"], x["Code_commune"]),
            axis=1
        )
        df = df.rename(columns={
            "Commune": "nom_commune",
            "Code_postal": "code_postal",
            "Code_departement": "code_departement"
        })
        df["region"] = None
        frames.append(df)
        print(f"📥 DVF {year}: {len(df)}")
    except Exception as e:
        print(f"⚠️ DVF {year}: {e}")

# =====================
# 3. INSEE
# =====================
for year in range(2017, 2022):
    try:
        df = pd.read_sql(f"""
            SELECT DISTINCT
                "CODGEO" AS code_insee,
                "LIBGEO" AS nom_commune
            FROM staging.insee_{year}
        """, engine)
        df["code_postal"] = None
        df["code_departement"] = None
        df["region"] = None
        frames.append(df)
        print(f"📥 INSEE {year}: {len(df)}")
    except Exception:
        continue

# =====================
# 4. ZONAGES
# =====================
cur = conn.cursor()
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'staging'
    AND table_name LIKE 'zonage_b%'
    ORDER BY table_name
""")
tables_zonage = [row[0] for row in cur.fetchall()]
cur.close()

print(f"\n📥 {len(tables_zonage)} tables zonage à traiter")

for table in tables_zonage:
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'staging'
        AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    cols_raw = [row[0] for row in cur.fetchall()]
    cur.close()

    # Nettoyer espaces et BOM
    cols_clean = {c.strip().upper(): c for c in cols_raw}

    col_insee = next(
        (cols_clean[cand.upper()] for cand in CANDIDATS_INSEE
         if cand.upper() in cols_clean),
        None
    )

    # Pour libcom : éviter de prendre la même colonne que INSEE
    col_libcom = next(
        (cols_clean[cand.upper()] for cand in CANDIDATS_LIBCOM
         if cand.upper() in cols_clean
         and cols_clean[cand.upper()] != col_insee),
        None
    )

    if col_insee is None:
        print(f"  ⚠ {table} — colonne INSEE non trouvée, colonnes: {list(cols_clean.keys())}")
        continue

    libcom_select = (
        f'TRIM("{col_libcom}") AS nom_commune'
        if col_libcom
        else "NULL AS nom_commune"
    )

    try:
        df = pd.read_sql(f"""
            SELECT DISTINCT
                TRIM("{col_insee}") AS code_insee,
                {libcom_select}
            FROM staging.{table}
            WHERE "{col_insee}" IS NOT NULL
        """, engine)

        df["code_insee"] = df["code_insee"].astype(str).str.strip().str.zfill(5)

        # Garder uniquement les vrais codes INSEE numériques à 5 chiffres
        df = df[df["code_insee"].str.match(r'^(\d{5}|2[AB]\d{3})$')]

        df["code_postal"] = None
        df["code_departement"] = None
        df["region"] = None

        frames.append(df)
        print(f"  ✓ {table} ({col_insee.strip()}) → {len(df)} communes")

    except Exception as e:
        print(f"  ⚠ {table}: {e}")

# ==================================================
# CONCAT + CLEAN
# ==================================================
df = pd.concat(frames, ignore_index=True)
df = clean_df(df)

# ==================================================
# NORMALISATION CODE POSTAL
# ==================================================
df["code_postal"] = pd.to_numeric(df["code_postal"], errors="coerce")
df["code_postal"] = (
    df["code_postal"]
    .fillna(0)
    .astype(int)
    .astype(str)
    .str.zfill(5)
)
df.loc[df["code_postal"] == "00000", "code_postal"] = None

# ==================================================
# SAFETY CHECK
# ==================================================
assert list(df.columns) == SCHEMA, "❌ Schema mismatch"

print(f"\n📊 FINAL DIM_COMMUNE: {len(df)} lignes")

# ==================================================
# LOAD
# ==================================================
cur = conn.cursor()
cur.execute("TRUNCATE TABLE silver.dim_commune CASCADE")

buffer = StringIO()
df.to_csv(buffer, index=False, header=False, na_rep="")
buffer.seek(0)

cur.copy_expert(f"""
    COPY silver.dim_commune ({", ".join(SCHEMA)})
    FROM STDIN WITH (FORMAT CSV, NULL '')
""", buffer)

conn.commit()
cur.close()
conn.close()

print("✅ silver.dim_commune chargé avec succès")