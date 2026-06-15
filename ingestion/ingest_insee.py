import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import io
import zipfile
import requests
import pandas as pd
from base_ingestor import BaseIngestor
from utils.config import load_config, get_base_dir
import os


class INSEEIngestor(BaseIngestor):

    def __init__(self, year: int, url: str, bronze_dir: str):
        self.year = year
        self.url = url
        output_path = os.path.join(bronze_dir, f"annee={year}", f"insee_{year}.parquet")
        super().__init__(output_path)

    def download(self) -> bytes:
        print(f"[INSEE] Téléchargement {self.year} depuis {self.url}")
        response = requests.get(self.url, stream=True)
        response.raise_for_status()
        return response.content

    def read(self, raw: bytes) -> pd.DataFrame:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            csv_files = [f for f in z.namelist() if f.endswith(".csv")]
            xlsx_files = [f for f in z.namelist() if "DEC_COM" in f and f.endswith(".xlsx")]

            if csv_files:
                with z.open(csv_files[0]) as f:
                    return pd.read_csv(f, low_memory=False, sep=";")

            if xlsx_files:
                with z.open(xlsx_files[0]) as f:
                    return pd.read_excel(f, engine="openpyxl", sheet_name="ENSEMBLE", header=5)

            raise ValueError(f"[INSEE] Aucun fichier reconnu dans le zip {self.year} : {z.namelist()}")


def ingest_all_insee():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["insee"]["bronze_dir"])
    fichiers = config["insee"]["fichiers"]

    for year, url in fichiers.items():
        INSEEIngestor(year, url, bronze_dir).run()


if __name__ == "__main__":
    ingest_all_insee()
