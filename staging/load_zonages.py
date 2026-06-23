import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import glob
import pandas as pd
from utils.config import load_config, get_base_dir
from utils.db import get_engine
from utils.validators import nettoyer_colonnes_sql

ENCODINGS = ["utf-8-sig", "latin-1", "utf-8", "cp1252", "iso-8859-1"]


def lire_fichier(filepath: str) -> pd.DataFrame | None:
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".csv":
            for enc in ENCODINGS:
                try:
                    return pd.read_csv(filepath, sep=";", dtype=str, encoding=enc)
                except UnicodeDecodeError:
                    continue

        elif ext == ".xls":
            try:
                return pd.read_excel(filepath, dtype=str, engine="xlrd")
            except Exception:
                # Fallback : lire comme HTML avec encodage Windows
                for enc in ["cp1252", "latin-1", "utf-8"]:
                    try:
                        with open(filepath, "rb") as f:
                            tables = pd.read_html(f, dtype_backend="numpy_nullable", encoding=enc)
                        if tables:
                            return tables[0].astype(str).replace("nan", pd.NA)
                    except Exception:
                        continue

        elif ext == ".xlsx":
            try:
                return pd.read_excel(filepath, dtype=str, engine="openpyxl")
            except Exception:
                pass
    except Exception as e:
        print(f"[ZONAGES] Erreur lecture {filepath} : {e}")
    return None


def extract_et_load_zonages(dossier: str, engine):
    total = 0
    for obs_code in sorted(os.listdir(dossier)):
        chemin_obs = os.path.join(dossier, obs_code)
        if not os.path.isdir(chemin_obs):
            continue

        dfs = []
        for fichier in glob.glob(os.path.join(chemin_obs, "*")):
            if not fichier.lower().endswith((".csv", ".xls", ".xlsx")):
                continue
            df = lire_fichier(fichier)
            if df is None:
                continue
            df.columns = [str(c).strip() for c in df.columns]
            df = nettoyer_colonnes_sql(df)
            df["observatory_b"] = obs_code
            df["source_file"] = os.path.basename(fichier)
            dfs.append(df)

        if not dfs:
            continue

        df_obs = pd.concat(dfs, ignore_index=True)
        table_name = f"zonage_{obs_code.lower()}"
        try:
            with engine.connect() as conn:
                df_obs.to_sql(table_name, schema="staging", con=conn, if_exists="replace", index=False)
                conn.commit()
            print(f"[ZONAGES] staging.{table_name} — {len(df_obs)} lignes")
            total += len(df_obs)
        except Exception as e:
            print(f"[ZONAGES] Erreur chargement {table_name} : {e}")

    print(f"[ZONAGES] Total : {total} lignes chargées")


def run_load_zonages():
    base_dir = get_base_dir()
    dossier = os.path.join(base_dir, "data", "bronze", "loyers_zonages")
    engine = get_engine()

    print("--- Chargement Zonages dans staging ---")
    extract_et_load_zonages(dossier, engine)
    print("Zonages staging terminé")


if __name__ == "__main__":
    run_load_zonages()
