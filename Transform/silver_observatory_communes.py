import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)

conn = psycopg2.connect(
    host=db["host"], port=db["port"],
    dbname=db["name"], user=db["user"],
    password=db["password"]
)

CANDIDATS_INSEE = ["INSEE", "CODE INSEE", "L6A", "CODE_INSEE", "COMMUNE"]

# ── 1. Communes et observatoires valides ──────────────────────────────────────
set_commune = set(pd.read_sql(
    "SELECT code_insee FROM silver.dim_commune", engine
)["code_insee"].astype(str).str.strip())

set_obs = set(pd.read_sql(
    "SELECT observatory_b FROM silver.dim_observatoire", engine
)["observatory_b"].astype(str).str.strip())

print(f"communes valides     : {len(set_commune)}")
print(f"observatoires valides: {len(set_obs)}")

# ── 2. Liste des tables zonage_b* ─────────────────────────────────────────────
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

print(f"\n{len(tables_zonage)} tables zonage trouvées")

# ── 3. Lire chaque table ──────────────────────────────────────────────────────
rows = []

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

    cols_clean = {c.strip().upper(): c for c in cols_raw}
    obs_code = table.replace("zonage_", "").upper()

    col_insee = next(
        (cols_clean[cand.upper()] for cand in CANDIDATS_INSEE
         if cand.upper() in cols_clean),
        None
    )

    if col_insee is None:
        print(f"  ⚠ {table} — colonne INSEE non trouvée")
        continue

    try:
        df = pd.read_sql(f"""
            SELECT DISTINCT TRIM("{col_insee}") AS code_insee
            FROM staging.{table}
            WHERE "{col_insee}" IS NOT NULL
        """, engine)

        df["code_insee"] = df["code_insee"].astype(str).str.strip().str.zfill(5)
        df = df[df["code_insee"].str.match(r'^(\d{5}|2[AB]\d{3})$')]
        df["observatory_b"] = obs_code

        rows.append(df)
        print(f"  ✓ {table} ({col_insee.strip()}) → {len(df)} communes")

    except Exception as e:
        print(f"  ⚠ {table}: {e}")

# ── 4. Consolider et filtrer FK ───────────────────────────────────────────────
df_bridge = pd.concat(rows, ignore_index=True).drop_duplicates()

avant = len(df_bridge)
df_bridge = df_bridge[
    df_bridge["code_insee"].isin(set_commune) &
    df_bridge["observatory_b"].isin(set_obs)
]

print(f"\nFK filter : {avant} → {len(df_bridge)} relations valides")
print(f"Communes couvertes     : {df_bridge['code_insee'].nunique()}")
print(f"Observatoires couverts : {df_bridge['observatory_b'].nunique()}")

# ── 5. Charger dans silver.bridge_commune_observatoire ────────────────────────
cur = conn.cursor()
cur.execute("TRUNCATE TABLE silver.bridge_commune_observatoire CASCADE;")

cur.executemany("""
    INSERT INTO silver.bridge_commune_observatoire (code_insee, observatory_b)
    VALUES (%s, %s)
    ON CONFLICT DO NOTHING;
""", df_bridge.itertuples(index=False, name=None))

conn.commit()
cur.close()
conn.close()

print("\n✅ bridge_commune_observatoire reconstruit")