import os                    # pour créer des dossiers, vérifier si un fichier existe
import requests              # pour télécharger des fichiers depuis internet
import pandas as pd          # pour lire le CSV et le convertir en Parquet
import yaml                  # pour lire le fichier config.yml
from io import StringIO      # pour lire le CSV depuis la réponse HTTP

# Charger la configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

# Get variables from config
url = config["communes"]["url"]
bronze_dir = os.path.join(BASE_DIR, config["communes"]["bronze_dir"])

def ingest_communes():
    output_path = f"{bronze_dir}/communes.parquet"

    # check if the file already exists
    if os.path.exists(output_path):
        print(f"File already exists : {output_path}")
        return

    # build the folder if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # download the CSV
    print(f"Downloading communes from {url}")
    response = requests.get(url)
    response.raise_for_status()

    # read the CSV
    print("Reading the CSV file...")
    df = pd.read_csv(
        StringIO(response.content.decode("utf-8")),
        sep=",",
        low_memory=False
    )

    # garder seulement les colonnes utiles
    cols_utiles = [
        "code_insee",
        "nom_standard",
        "epci_code",
        "epci_nom",
        "nom_unite_urbaine",
        "code_postal",
        "reg_code",
        "reg_nom",
        "dep_code",
        "dep_nom",
        "latitude_mairie",
        "longitude_mairie",
        "population"
    ]
    df = df[cols_utiles].copy()

    # save as parquet
    print(f"Saving to {output_path}")
    df.to_parquet(output_path, index=False)
    print(f"Terminé : {output_path} ({len(df)} communes)")


if __name__ == "__main__":
    ingest_communes()