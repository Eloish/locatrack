import os
import pandas as pd
from utils.validators import validate_file


class BaseIngestor:
    """
    Classe de base pour tous les ingesteurs bronze.
    Chaque sous-classe implémente download() et read().

    Idempotence :
      - already_ingested() vérifie que le fichier existe, est non vide et lisible.
      - Un fichier corrompu ou tronqué sera réingéré automatiquement.
    """

    def __init__(self, output_path: str):
        self.output_path = output_path

    def already_ingested(self) -> bool:
        return validate_file(self.output_path)

    def download(self) -> bytes:
        raise NotImplementedError

    def read(self, raw: bytes) -> pd.DataFrame:
        raise NotImplementedError

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise ValueError(f"[INGESTOR] DataFrame vide après lecture : {self.output_path}")
        return df

    def save(self, df: pd.DataFrame):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        df.to_parquet(self.output_path, index=False)
        print(f"[INGESTOR] Sauvegardé : {self.output_path} ({len(df)} lignes)")

    def run(self):
        if self.already_ingested():
            print(f"[INGESTOR] Déjà présent et valide : {self.output_path}")
            return
        raw = self.download()
        df = self.read(raw)
        df = self.validate(df)
        self.save(df)
