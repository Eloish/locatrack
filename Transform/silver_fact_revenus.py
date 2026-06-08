import os
import pandas as pd
import psycopg2
from io import StringIO
from sqlalchemy import create_engine
import yaml

# ── 1. GESTION DES CONFIGURATIONS ET CONNEXIONS ──────────────────────────────
def load_database_connections():
    """Charge la configuration et initialise les moteurs de connexion."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config.yml")

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
    return engine, conn


# ── 2. LOGIQUE DE NETTOYAGE ET TRANSFORMATION (TRANSFORM) ─────────────────────
def nettoyer_float(series):
    """Nettoie les chaînes de caractères contenant des virgules en floats valides."""
    if series.dtype == object:
        return (
            series.astype(str)
            .str.replace(",", ".")
            .pipe(pd.to_numeric, errors="coerce")
        )
    return pd.to_numeric(series, errors="coerce")

def extract_and_transform_revenus(engine):
    """Boucle sur les tables de staging de l'INSEE pour extraire et transformer les revenus."""
    col_revenu_par_annee = {
        2017: "Q217",
        2018: "Q218",
        2019: "Q219",
        2020: "Q220",
        2021: "Q221",
    }

    rows = []

    for annee, col_revenu in col_revenu_par_annee.items():
        print(f"  -> Traitement INSEE {annee} ({col_revenu})...")
        
        df_insee = pd.read_sql(f"""
            SELECT 
                "CODGEO" as code_insee,
                "{col_revenu}"::text as revenu_median
            FROM staging.insee_{annee}
            WHERE "{col_revenu}"::text != 's'
            AND "{col_revenu}" IS NOT NULL
        """, engine)

        # Transformations géométriques / calculs métiers
        df_insee["revenu_median"] = nettoyer_float(df_insee["revenu_median"])
        df_insee["revenu_mensuel"] = df_insee["revenu_median"] / 12
        df_insee["annee"] = annee

        # Sécurité : suppression des lignes dont le revenu n'a pas pu être converti
        df_insee = df_insee.dropna(subset=["revenu_median"])

        rows.append(df_insee[["code_insee", "annee", "revenu_median", "revenu_mensuel"]])
        print(f"     ✓ {len(df_insee)} communes récupérées")

    if not rows:
        return pd.DataFrame()

    df_final = pd.concat(rows, ignore_index=True)
    
    # Normalisation stricte du code INSEE (5 caractères)
    df_final["code_insee"] = df_final["code_insee"].astype(str).str.strip().str.zfill(5)
    
    return df_final


# ── 3. CHARGEMENT DANS POSTGRESQL (LOAD) ─────────────────────────────────────
def load_fact_revenus(conn, engine, df_final):
    """Valide l'intégrité référentielle et injecte les données via COPY."""
    print("\n🔍 Validation de l'intégrité avec silver.dim_commune...")
    
    # Récupération des codes valides dans la dimension
    valid_codes = set(pd.read_sql("SELECT code_insee FROM silver.dim_commune", engine)["code_insee"].astype(str))
    missing_codes = set(df_final["code_insee"]) - valid_codes

    # Grâce au script de dimension blindé, missing_codes devrait être vide
    if missing_codes:
        missing_count = df_final[df_final["code_insee"].isin(missing_codes)].shape[0]
        print(f"  ⚠️ Attention : {missing_count} lignes INSEE ignorées (codes absents de dim_commune).")
        df_final = df_final[df_final["code_insee"].isin(valid_codes)].copy()

    if df_final.empty:
        print("❌ Erreur : Aucune ligne valide à insérer dans silver.fact_revenus.")
        return

    print(f"📥 Chargement de {len(df_final)} lignes dans silver.fact_revenus...")
    cur = conn.cursor()
    try:
        # On vide la table fact avant de recharger (Idempotence)
        cur.execute("TRUNCATE TABLE silver.fact_revenus")
        
        # Passage par un buffer mémoire (CSV virtuel) pour activer le COPY rapide
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
        print(f"✅ FÉLICITATIONS : silver.fact_revenus remplie avec succès ! 🚀")
    except Exception as e:
        conn.rollback()
        print(f"❌ ERREUR DURANT LE COPY : {e}")
        raise e
    finally:
        cur.close()


# ── 4. ORCHESTRATION GÉNÉRALE (MAIN) ─────────────────────────────────────────
# ── 4. ORCHESTRATION GÉNÉRALE (MAIN) ─────────────────────────────────────────
def main():
    print("🚀 DÉBUT DU PIPELINE FACT_REVENUS (SOLID VERSION)\n")
    
    engine, conn = load_database_connections()
    
    try:
        # 1. Extract & Transform (Correction du nom de la fonction ici)
        df_revenus = extract_and_transform_revenus(engine)
        
        # 2. Load
        if not df_revenus.empty:
            load_fact_revenus(conn, engine, df_revenus)
        else:
            print("⚠ Aucune donnée trouvée dans les tables de staging INSEE.")
            
    finally:
        # Sécurité : On s'assure de fermer proprement la connexion, quoi qu'il arrive
        conn.close()
        print("\n🔒 Connexions à la base de données fermées proprement.")

if __name__ == "__main__":
    main()