import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import pandas as pd
from io import BytesIO, StringIO
from base_ingestor import BaseIngestor
from utils.config import load_config, get_base_dir
import os


class LoyersParquetIngestor(BaseIngestor):

    def __init__(self, year: int, url: str, bronze_dir: str):
        self.year = year
        self.url = url
        output_path = os.path.join(bronze_dir, f"annee={year}", f"loyers_{year}.parquet")
        super().__init__(output_path)

    def download(self) -> bytes:
        print(f"[LOYERS] Téléchargement parquet {self.year} depuis {self.url}")
        response = requests.get(self.url, stream=True)
        response.raise_for_status()
        return response.content

    def read(self, raw: bytes) -> pd.DataFrame:
        return pd.read_parquet(BytesIO(raw))


class LoyersCSVIngestor(BaseIngestor):

    def __init__(self, year: int, url: str, bronze_dir: str):
        self.year = year
        self.url = url
        output_path = os.path.join(bronze_dir, f"annee={year}", f"loyers_{year}.parquet")
        super().__init__(output_path)

    def download(self) -> bytes:
        print(f"[LOYERS] Téléchargement CSV {self.year} depuis {self.url}")
        response = requests.get(self.url, stream=True)
        response.raise_for_status()
        return response.content

    def read(self, raw: bytes) -> pd.DataFrame:
        return pd.read_csv(StringIO(raw.decode("utf-8")), low_memory=False, sep=";")


def ingest_all_loyers():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["loyers"]["bronze_dir"])
    fichiers_parquet = config["loyers"]["fichiers_parquet"]
    fichiers_csv = config["loyers"]["fichiers_csv"]

    for year, url in fichiers_parquet.items():
        LoyersParquetIngestor(year, url, bronze_dir).run()

    for year, url in fichiers_csv.items():
        LoyersCSVIngestor(year, url, bronze_dir).run()


if __name__ == "__main__":
    ingest_all_loyers()
