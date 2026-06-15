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


class DVFIngestor(BaseIngestor):

    def __init__(self, year: int, url: str, bronze_dir: str):
        self.year = year
        self.url = url
        output_path = os.path.join(bronze_dir, f"annee={year}", f"dvf_{year}.parquet")
        super().__init__(output_path)

    def download(self) -> bytes:
        print(f"[DVF] Téléchargement {self.year} depuis {self.url}")
        response = requests.get(self.url, stream=True)
        response.raise_for_status()
        return response.content

    def read(self, raw: bytes) -> pd.DataFrame:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            csv_filename = z.namelist()[0]
            with z.open(csv_filename) as f:
                return pd.read_csv(f, low_memory=False, sep="|")


def ingest_all_dvf():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["dvf"]["bronze_dir"])
    fichiers = config["dvf"]["fichiers"]

    for year, url in fichiers.items():
        DVFIngestor(year, url, bronze_dir).run()


if __name__ == "__main__":
    ingest_all_dvf()
