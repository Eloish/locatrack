import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import zipfile
import pandas as pd
from io import BytesIO
from utils.config import load_config, get_base_dir
from utils.db import get_engine
from utils.loader import upsert_to_staging

EXCEL_NAME = "table-appartenance-geo-communes-2025.xlsx"


def extract_excel(bronze_dir: str) -> bytes:
    zip_path = os.path.join(bronze_dir, "table-appartenance-geo-communes-2025.zip")
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"[REF_GEO] ZIP manquant : {zip_path} — lance d'abord ingest_ref_geo.py")
    with zipfile.ZipFile(zip_path) as z:
        with z.open(EXCEL_NAME) as f:
            return f.read()


def read_communes_geo(data: bytes) -> pd.DataFrame:
    df = pd.read_excel(
        BytesIO(data), sheet_name="COM", engine="calamine",
        header=5, dtype=str
    )
    return df[["CODGEO", "LIBGEO", "DEP", "REG", "UU2020"]].rename(columns={
        "CODGEO": "code_insee",
        "LIBGEO": "nom_commune",
        "DEP":    "dep",
        "REG":    "reg",
        "UU2020": "uu2020",
    }).dropna(subset=["code_insee"])


def read_uu2020(data: bytes) -> pd.DataFrame:
    df = pd.read_excel(
        BytesIO(data), sheet_name="Zones_supra_communales", engine="calamine",
        header=5, dtype=str
    )
    uu = df[df["NIVGEO"] == "UU2020"][["CODGEO", "LIBGEO", "NB_COM"]].rename(columns={
        "CODGEO": "uu2020",
        "LIBGEO": "nom_uu",
        "NB_COM": "nb_communes",
    })
    return uu.dropna(subset=["uu2020"])


def run_load_ref_geo():
    config     = load_config()
    base_dir   = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["ref_geo"]["bronze_dir"])
    engine     = get_engine()

    print("[REF_GEO] Lecture du ZIP bronze...")
    data = extract_excel(bronze_dir)

    print("[REF_GEO] Chargement staging.communes_geo...")
    df_communes = read_communes_geo(data)
    upsert_to_staging(engine, df_communes, "communes_geo")
    print(f"[REF_GEO] {len(df_communes)} communes chargées")

    print("[REF_GEO] Chargement staging.uu2020...")
    df_uu = read_uu2020(data)
    upsert_to_staging(engine, df_uu, "uu2020")
    print(f"[REF_GEO] {len(df_uu)} unités urbaines chargées")

    print("[REF_GEO] Load staging terminé.")


if __name__ == "__main__":
    run_load_ref_geo()
