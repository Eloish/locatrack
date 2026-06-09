import os
import glob
import pandas as pd
from sqlalchemy import create_engine
import yaml

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@"
    f"{db['host']}:{db['port']}/{db['name']}"
)

DOSSIER_ZONAGES = os.path.join(
    BASE_DIR,
    "data",
    "bronze",
    "loyers_zonages"
)

ENCODINGS = [
    "utf-8-sig",
    "latin-1",
    "utf-8",
    "cp1252",
    "iso-8859-1"
]

# ============================================================
# LECTURE ROBUSTE
# ============================================================

def lire_fichier(filepath):

    ext = os.path.splitext(filepath)[1].lower()

    try:

        if ext == ".csv":

            for enc in ENCODINGS:

                try:

                    df = pd.read_csv(
                        filepath,
                        sep=";",
                        dtype=str,
                        encoding=enc
                    )

                    return df

                except UnicodeDecodeError:
                    continue

        elif ext in [".xls", ".xlsx"]:

            return pd.read_excel(
                filepath,
                dtype=str
            )

    except Exception as e:

        print(f"❌ Erreur lecture {filepath}")
        print(e)

    return None

# ============================================================
# EXTRACTION
# ============================================================

dfs = []

print("🚀 Chargement des zonages vers STAGING")

for obs_code in sorted(os.listdir(DOSSIER_ZONAGES)):

    chemin_obs = os.path.join(
        DOSSIER_ZONAGES,
        obs_code
    )

    if not os.path.isdir(chemin_obs):
        continue

    print(f"\n📂 {obs_code}")

    fichiers = glob.glob(
        os.path.join(chemin_obs, "*")
    )

    for fichier in fichiers:

        if not fichier.lower().endswith(
            (".csv", ".xls", ".xlsx")
        ):
            continue

        df = lire_fichier(fichier)

        if df is None:
            continue

        # garde les colonnes d'origine
        df.columns = [str(c).strip() for c in df.columns]

        # métadonnées techniques
        df["observatory_b"] = obs_code
        df["source_file"] = os.path.basename(fichier)

        dfs.append(df)

        print(
            f"   ✓ {os.path.basename(fichier)} "
            f"({len(df)} lignes)"
        )

# ============================================================
# CONCAT
# ============================================================

if not dfs:

    print("❌ Aucun fichier chargé")
    exit()

df_final = pd.concat(
    dfs,
    ignore_index=True,
    sort=False
)

print("\n📊 Résumé")
print("Lignes :", len(df_final))
print("Colonnes :", len(df_final.columns))

# ============================================================
# CHARGEMENT STAGING
# ============================================================

df_final.to_sql(
    name="zonage_brut",
    schema="staging",
    con=engine,
    if_exists="replace",
    index=False
)

print("\n✅ staging.zonage_brut chargé avec succès")