import os
import glob
import pandas as pd

# 1. Configuration des chemins
# Remonte deux fois pour sortir du dossier 'Exploration' et arriver à la racine 'locatrack'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_ZONAGES = os.path.join(BASE_DIR, "data/bronze/loyers_zonages")
OUTPUT_FILE = os.path.join(BASE_DIR, "data/mapping_observatory_communes.csv")

ENCODINGS = ["utf-8-sig", "latin-1", "utf-8", "cp1252", "iso-8859-1"]

def lire_fichier_robuste(filepath: str) -> pd.DataFrame | None:
    """Détecte l'extension et lit le fichier automatiquement (CSV ou Excel)."""
    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        # Cas 1 : Fichiers CSV
        if ext == '.csv':
            for enc in ENCODINGS:
                try:
                    df = pd.read_csv(filepath, sep=";", dtype=str, encoding=enc)
                    # Nettoyage automatique : on enlève BOM et espaces
                    df.columns = df.columns.str.replace('\ufeff', '').str.strip()
                    return df
                except UnicodeDecodeError:
                    continue
        
        # Cas 2 : Fichiers Excel (.xls, .xlsx)
        elif ext in ['.xls', '.xlsx']:
            df = pd.read_excel(filepath, dtype=str)
            df.columns = df.columns.str.strip() # Nettoyage espaces
            return df
            
    except Exception as e:
        print(f"  ⚠ Erreur lecture {filepath} : {e}")
    
    return None

def trouver_colonne(df: pd.DataFrame, candidats: list[str]) -> str | None:
    """Trouve la première colonne qui matche un des noms candidats (insensible à la casse)."""
    cols_upper = {c.upper(): c for c in df.columns}
    for candidat in candidats:
        if candidat.upper() in cols_upper:
            return cols_upper[candidat.upper()]
    return None

def construire_mapping(dossier: str) -> pd.DataFrame:
    rows = []

    for obs_code in sorted(os.listdir(dossier)):
        chemin_obs = os.path.join(dossier, obs_code)
        if not os.path.isdir(chemin_obs):
            continue

        # On cherche tout fichier contenant "onage" peu importe l'extension (*.*)
        fichiers = [f for f in glob.glob(os.path.join(chemin_obs, "*onage*.*")) 
                    if f.lower().endswith(('.csv', '.xls', '.xlsx'))]
        
        if not fichiers:
            print(f"⚠ Pas de fichier Zonage compatible dans : {obs_code}")
            continue

        for f in fichiers:
            df = lire_fichier_robuste(f)
            if df is None: continue

            # --- LISTES ÉTENDUES DE CANDIDATS ---
            col_insee = trouver_colonne(df, ["INSEE", "INSEE_COM", "Commune", "COD_COM", "CODE_INSEE", "CODE INSEE", "L6a", "L6A", "code_insee", "code_iris"])
            col_libcom = trouver_colonne(df, ["Lib_com", "LIB_COM", "Libelle", "NOM_COM", "nom_com", "LIBCOM", "Libcom", "NOM_COMMUNE"])
            col_zone = trouver_colonne(df, ["Zone", "ZONE", "zone", "num_zone", "LIBZONE", "LIB_ZONE"])
            col_libzone = trouver_colonne(df, ["Lib_zone", "LIB_ZONE", "lib_zone", "libelle_zone", "LIB_IRIS"])

            if col_insee is None:
                print(f"  ⚠ Pas de colonne INSEE identifiée dans {obs_code} ({os.path.basename(f)}). Colonnes : {list(df.columns)}")
                continue

            # Construction du dataframe
            df_out = pd.DataFrame()
            df_out["code_insee"]  = df[col_insee].str.strip().str.zfill(5)
            df_out["nom_commune"] = df[col_libcom].str.strip() if col_libcom else "Inconnu"
            df_out["zone"]        = df[col_zone].str.strip()   if col_zone     else "Inconnu"
            df_out["lib_zone"]    = df[col_libzone].str.strip() if col_libzone else "Inconnu"
            df_out["observatory_b"] = obs_code

            # Dédupliquer par code INSEE
            df_out = df_out.drop_duplicates(subset=["code_insee"])
            rows.append(df_out)
            
            print(f"✓ {obs_code} traité : {len(df_out)} communes")

    if not rows:
        print("❌ Aucune donnée extraite")
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True).drop_duplicates(
        subset=["observatory_b", "code_insee"]
    )

if __name__ == "__main__":
    if not os.path.exists(DOSSIER_ZONAGES):
        print(f"❌ Le dossier {DOSSIER_ZONAGES} n'existe pas.")
    else:
        df_mapping = construire_mapping(DOSSIER_ZONAGES)

        if not df_mapping.empty:
            print(f"\n📊 Résultat :")
            print(f"  Observatoires : {df_mapping['observatory_b'].nunique()}")
            print(f"  Communes      : {df_mapping['code_insee'].nunique()}")
            df_mapping.to_csv(OUTPUT_FILE, index=False)
            print(f"\n✅ Sauvegardé : {OUTPUT_FILE}")