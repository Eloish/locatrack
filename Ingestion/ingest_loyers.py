import os
import requests
import pandas as pd
import yaml
from io import BytesIO, StringIO

# Charger la configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

# Get variables from config
fichiers_parquet = config["loyers"]["fichiers_parquet"]
fichiers_csv = config["loyers"]["fichiers_csv"]
bronze_dir = os.path.join(BASE_DIR, config["loyers"]["bronze_dir"])

# Toutes les années disponibles
years = sorted(set(list(fichiers_parquet.keys()) + list(fichiers_csv.keys())))


def ingest_loyers(year: int):
    # define the path to the bronze directory
    output_path = f"{bronze_dir}/annee={year}/loyers_{year}.parquet"

    # check if the file already exists
    if os.path.exists(output_path):
        print(f"File for year {year} already exists")
        return

    # build the folder if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # cas 1 : fichier Parquet direct
    if year in fichiers_parquet:
        url = fichiers_parquet[year]
        print(f"Downloading Parquet for year {year} from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        df = pd.read_parquet(BytesIO(response.content))

    # cas 2 : fichier CSV
    elif year in fichiers_csv:
        url = fichiers_csv[year]
        print(f"Downloading CSV for year {year} from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), low_memory=False, sep=";")

    # save the dataframe as parquet
    print(f"Saving the data for year {year} to {output_path}")
    df.to_parquet(output_path, index=False)
    print(f"[{year}] Terminé : {output_path}")


# Ingest data for all years
if __name__ == "__main__":
    for year in years:
        ingest_loyers(year)