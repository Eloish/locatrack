import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from utils.config import load_config, get_base_dir


def run_ingest_ref_geo():
    config = load_config()
    base_dir = get_base_dir()
    bronze_dir = os.path.join(base_dir, config["ref_geo"]["bronze_dir"])
    url = config["ref_geo"]["table_appartenance_url"]

    os.makedirs(bronze_dir, exist_ok=True)
    dest = os.path.join(bronze_dir, "table-appartenance-geo-communes-2025.zip")

    if os.path.exists(dest):
        print(f"[REF_GEO] Déjà téléchargé : {dest}")
        return

    print(f"[REF_GEO] Téléchargement depuis {url}")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    with open(dest, "wb") as f:
        f.write(response.content)
    print(f"[REF_GEO] Sauvegardé : {dest} ({len(response.content) // 1024} Ko)")


if __name__ == "__main__":
    run_ingest_ref_geo()
