import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import pandas as pd
from io import StringIO
from base_ingestor import BaseIngestor
from utils.config import load_config, get_base_dir
import os

COLS_UTILES = [
    "code_insee", "nom_standard", "epci_code", "epci_nom",
    "nom_unite_urbaine", "code_postal", "reg_code", "reg_nom",
    "dep_code", "dep_nom", "latitude_mairie", "longitude_mairie", "population",
]


class CommunesIngestor(BaseIngestor):

    def __init__(self, url: str, bronze_dir: str):
        self.url = url
        output_path = os.path.join(bronze_dir, "communes.parquet")
        super().__init__(output_path)

    def download(self) -> bytes:
        print(f"[COMMUNES] Téléchargement depuis {self.url}")
        response = requests.get(self.url)
        response.raise_for_status()
        return response.content

    def read(self, raw: bytes) -> pd.DataFrame:
        df = pd.read_csv(StringIO(raw.decode("utf-8")), sep=",", low_memory=False)
        available = [c for c in COLS_UTILES if c in df.columns]
        return df[available].copy()


def ingest_communes():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["communes"]["bronze_dir"])
    url = config["communes"]["url"]
    CommunesIngestor(url, bronze_dir).run()


if __name__ == "__main__":
    ingest_communes()
