import os
import glob
import pandas as pd

BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_ZONAGES = os.path.join(BASE_DIR, "data/bronze/loyers_zonages")

ENCODINGS = ["latin-1", "utf-8", "cp1252", "iso-8859-1"]

def lire_csv_robuste(filepath: str) -> pd.DataFrame | None:
    """Essaie plusieurs encodages jusqu'à ce que ça marche."""
    for enc in ENCODINGS:
        try:
            df = pd.read_csv(filepath, sep=";", dtype=str, encoding=enc)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"  ⚠ Erreur inattendue ({enc}) : {e}")
            return None
    print(f"  ⚠ Aucun encodage ne fonctionne pour : {filepath}")
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

        fichiers = glob.glob(os.path.join(chemin_obs, "*onage*.csv"))
        if not fichiers:
            print(f"⚠ Pas de fichier Zonage dans : {obs_code}")
            continue

        for f in fichiers:
            df = lire_csv_robuste(f)
            if df is None:
                continue

            print(f"  Colonnes {obs_code} : {list(df.columns)}")

            # Colonne INSEE — plusieurs noms possibles
            col_insee = trouver_colonne(df, ["INSEE", "INSEE_COM", "Commune", "COD_COM"])
            if col_insee is None:
                print(f"  ⚠ Pas de colonne INSEE dans {obs_code} : {list(df.columns)}")
                continue

            # Colonne nom commune
            col_libcom = trouver_colonne(df, ["Lib_com", "LIB_COM", "Libelle", "NOM_COM", "nom_com"])

            # Colonne zone
            col_zone = trouver_colonne(df, ["Zone", "ZONE", "zone", "num_zone"])

            # Colonne libellé zone
            col_libzone = trouver_colonne(df, ["Lib_zone", "LIB_ZONE", "lib_zone", "libelle_zone"])

            # Construire le dataframe avec les colonnes trouvées
            df_out = pd.DataFrame()
            df_out["code_insee"]  = df[col_insee].str.strip().str.zfill(5)
            df_out["nom_commune"] = df[col_libcom].str.strip() if col_libcom else ""
            df_out["zone"]        = df[col_zone].str.strip()   if col_zone    else ""
            df_out["lib_zone"]    = df[col_libzone].str.strip() if col_libzone else ""
            df_out["observatory_b"] = obs_code

            # Dédupliquer par commune (plusieurs lignes par IRIS)
            df_out = df_out.drop_duplicates(subset=["code_insee"])

            rows.append(df_out)
            print(f"✓ {obs_code} : {df_out['code_insee'].nunique()} communes")

    if not rows:
        print("❌ Aucune donnée extraite")
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True).drop_duplicates(
        subset=["observatory_b", "code_insee"]
    )


if __name__ == "__main__":
    df_mapping = construire_mapping(DOSSIER_ZONAGES)

    print(f"\n📊 Résultat :")
    print(f"  Observatoires : {df_mapping['observatory_b'].nunique()}")
    print(f"  Communes      : {df_mapping['code_insee'].nunique()}")
    print(f"\nPar observatoire :")
    print(df_mapping.groupby("observatory_b")["code_insee"].count()
          .sort_values(ascending=False).to_string())

    out = os.path.join(BASE_DIR, "data/mapping_observatory_communes.csv")
    df_mapping.to_csv(out, index=False)
    print(f"\n✅ Sauvegardé : {out}")