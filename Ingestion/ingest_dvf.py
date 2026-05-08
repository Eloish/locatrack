import os                   
import requests             
import zipfile              
import io                   
import pandas as pd          
import yaml                

# Charger la configuration depuis le fichier config.yml
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

# Get variables from config
fichiers = config["dvf"]["fichiers"]      # dictionnaire {annee: url}
bronze_dir = os.path.join(BASE_DIR, config["dvf"]["bronze_dir"])
years = list(fichiers.keys())             # [2021, 2022, 2023, 2024, 2025]


def ingest_dvf(year: int):
    # define the path to the bronze directory
    output_path = f"{bronze_dir}/annee={year}/dvf_{year}.parquet"

    # check if the file already exists
    if os.path.exists(output_path):
        print(f"File for year {year} already exists")
        return

    # build the folder if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # get the url for this year from config
    url = fichiers[year]
    print(f"Downloading data for year {year} from {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()  # check if the request was successful

    # read the zip file in memory
    print(f"Reading the zip file for year {year}")
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip:
        csv_filename = zip.namelist()[0]
        with zip.open(csv_filename) as f:
            df = pd.read_csv(f, low_memory=False, sep="|")

    # save the dataframe as parquet
    print(f"Saving the data for year {year} to {output_path}")
    df.to_parquet(output_path, index=False)
    print(f"[{year}] Terminé : {output_path}")


# Ingest data for all years
if __name__ == "__main__":
    for year in years:
        ingest_dvf(year)