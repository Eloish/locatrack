import os
import requests
import zipfile
import io
import pandas as pd
import yaml

# Charger la configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

# Get variables from config
fichiers = config["insee"]["fichiers"]
bronze_dir = os.path.join(BASE_DIR, config["insee"]["bronze_dir"])
years = list(fichiers.keys())


def ingest_insee(year: int):
    output_path = f"{bronze_dir}/annee={year}/insee_{year}.parquet"

    if os.path.exists(output_path):
        print(f"File for year {year} already exists")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    url = fichiers[year]
    print(f"Downloading data for year {year} from {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    print(f"Reading the zip file for year {year}")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        print(f"Files found in zip : {z.namelist()}")

        
        csv_files = [f for f in z.namelist() if f.endswith(".csv")]
        xlsx_files = [f for f in z.namelist() if "DEC_COM" in f and f.endswith(".xlsx")]

        if csv_files:
            print(f"Reading CSV : {csv_files[0]}")
            with z.open(csv_files[0]) as f:
                df = pd.read_csv(f, low_memory=False, sep=";")

        elif xlsx_files:
            print(f"Reading XLSX : {xlsx_files[0]}")
            with z.open(xlsx_files[0]) as f:
                df = pd.read_excel(
                    f, 
                    engine="openpyxl",
                    sheet_name="ENSEMBLE",  # onglet avec toutes les communes
                    header=5  # les vraies en-têtes commencent à la ligne 5
                )

        else:
            print(f"[{year}] Aucun fichier reconnu dans le zip : {z.namelist()}")
            return

    print(f"Saving the data for year {year} to {output_path}")
    df.to_parquet(output_path, index=False)
    print(f"[{year}] Terminé : {output_path}")


# Ingest data for all years
if __name__ == "__main__":
    for year in years:
        ingest_insee(year)