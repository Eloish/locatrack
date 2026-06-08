import pandas as pd
from sqlalchemy import create_engine, text
import os
import yaml
import re
import unicodedata

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]

engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@"
    f"{db['host']}:{db['port']}/{db['name']}"
)

# ============================================================
# CLEANING FUNCTION
# ============================================================
def clean_text(x):
    if pd.isna(x):
        return x

    x = str(x)

    # normalisation unicode correcte
    x = unicodedata.normalize("NFKC", x)

    # suppression caractères invisibles
    x = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', x)

    # nettoyage espaces
    x = re.sub(r'\s+', ' ', x)

    return x.strip()
# ============================================================
# MAIN ETL
# ============================================================

def load_mapping():

    print("🚀 Chargement du mapping observatoire-communes...")

    file_path = os.path.join(BASE_DIR, "data/mapping_observatory_communes.csv")

    # 1. Lecture CSV
    df = pd.read_csv(
    file_path,
    encoding="cp1252",
    dtype=str
)
    print(df[df["nom_commune"].str.contains("�", na=False)])

    print(f"📊 Lignes initiales : {len(df)}")

    # 2. Nettoyage global texte
    for col in df.select_dtypes(include=["string", "object"]).columns:
        df[col] = df[col].apply(clean_text)

    # 3. Normalisation code INSEE
    df["code_insee"] = df["code_insee"].astype(str).str.zfill(5)

    # 4. Suppression doublons métier
    df = df.drop_duplicates(subset=["code_insee", "observatory_b"])

    print(f"🧹 Après nettoyage : {len(df)} lignes")

    # 5. Création schéma ref
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ref"))

    # 6. Chargement en base
    df.to_sql(
        name="mapping_communes",
        con=engine,
        schema="ref",
        if_exists="replace",
        index=False
    )

    print("✅ ref.mapping_communes chargé avec succès")


if __name__ == "__main__":
    load_mapping()