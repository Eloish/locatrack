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

        elif ext in [".xls", ".xlsx"]:
            try:
                return pd.read_excel(filepath, dtype=str)
            except Exception:
                tables = pd.read_html(filepath, dtype_backend="numpy_nullable")
                if tables:
                    df = tables[0].astype(str).replace("nan", pd.NA)
                    return df
    except Exception as e:
        print(f"[ZONAGES] Erreur lecture {filepath} : {e}")
    return None


def extract_zonages(dossier: str) -> pd.DataFrame:
    dfs = []
    for obs_code in sorted(os.listdir(dossier)):
        chemin_obs = os.path.join(dossier, obs_code)
        if not os.path.isdir(chemin_obs):
            continue
        for fichier in glob.glob(os.path.join(chemin_obs, "*")):
            if not fichier.lower().endswith((".csv", ".xls", ".xlsx")):
                continue
            df = lire_fichier(fichier)
            if df is None:
                continue
            df.columns = [str(c).strip() for c in df.columns]
            df["observatory_b"] = obs_code
            df["source_file"] = os.path.basename(fichier)
            dfs.append(df)
            print(f"[ZONAGES] {obs_code}/{os.path.basename(fichier)} — {len(df)} lignes")

    if not dfs:
        raise ValueError("[ZONAGES] Aucun fichier chargé")
    return pd.concat(dfs, ignore_index=True, sort=False)


def transform_zonages(df: pd.DataFrame) -> pd.DataFrame:
    return nettoyer_colonnes_sql(df)


def load_zonages(df: pd.DataFrame, engine):
    df.to_sql("zonage_brut", schema="staging", con=engine, if_exists="replace", index=False)
    print(f"[ZONAGES] staging.zonage_brut — {len(df)} lignes chargées")


def run_load_zonages():
    base_dir = get_base_dir()
    dossier = os.path.join(base_dir, "data", "bronze", "loyers_zonages")
    engine = get_engine()

    print("--- Chargement Zonages dans staging ---")
    df = extract_zonages(dossier)
    df = transform_zonages(df)
    load_zonages(df, engine)
    print("Zonages staging terminé")


if __name__ == "__main__":
    run_load_zonages()
