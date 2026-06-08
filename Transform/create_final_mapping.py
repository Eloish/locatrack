import pandas as pd
from sqlalchemy import create_engine, text
import os
import yaml

# 1. Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)
db = config["database"]

# Connexion DB
engine = create_engine(f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}")

def create_mapping_table():
    print("🚀 Création de la table ref.mapping_communes...")

    # A. Créer le schéma 'ref' s'il n'existe pas
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ref"))
        conn.commit()

    # B. Charger le mapping brut
    df_mapping = pd.read_csv(os.path.join(BASE_DIR, "data/mapping_observatory_communes.csv"), 
                             encoding='latin1', dtype=str)
    
    # C. Charger les agglomérations depuis la base
    df_agglos = pd.read_sql("SELECT observatory_b, nom_agglomeration FROM silver.dim_agglomeration", engine)
    
    # D. Le MERGE
    df_final = df_mapping.merge(df_agglos, on="observatory_b", how="left")
    
    # E. Nettoyage rapide avant insertion
    df_final['code_insee'] = df_final['code_insee'].str.zfill(5)
    
    # F. ENVOI EN BASE (Le changement est ici)
    # On remplace ('replace') la table à chaque fois pour être sûr d'avoir les dernières données
    df_final.to_sql('mapping_communes', engine, schema='ref', if_exists='replace', index=False)
    
    print("✅ Table ref.mapping_communes mise à jour dans la base.")
    print(f"   Nombre de lignes insérées : {len(df_final)}")

if __name__ == "__main__":
    create_mapping_table()