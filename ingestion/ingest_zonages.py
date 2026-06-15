import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import zipfile
import io
import os
import time
import re
import glob
import pandas as pd
from utils.config import get_base_dir

BASE_DIR = get_base_dir()
OUT_DIR = os.path.join(BASE_DIR, "data/bronze/loyers_zonages")
DOSSIER_LOYERS = os.path.join(BASE_DIR, "data/bronze/loyers")


def extraire_obs_depuis_url(url: str) -> str | None:
    match = re.search(r'_L(\d{1,2}[AB]\d{2}|\d{4})\.zip', url, re.IGNORECASE)
    if match:
        return "B" + match.group(1).upper()
    return None


def collecter_observatoires_cibles() -> set:
    fichiers = glob.glob(os.path.join(DOSSIER_LOYERS, "**", "*.parquet"), recursive=True)
    if not fichiers:
        raise FileNotFoundError(f"[ZONAGES] Aucun parquet trouvé dans {DOSSIER_LOYERS}")

    obs = set()
    for f in fichiers:
        try:
            df = pd.read_parquet(f, columns=["Observatory"])
            obs.update(df["Observatory"].dropna().unique())
        except Exception as e:
            print(f"[ZONAGES] Impossible de lire {os.path.basename(f)} : {e}")
    return obs


def recuperer_zips_api() -> list:
    url = "https://www.data.gouv.fr/api/1/datasets/resultats-des-observatoires-locaux-des-loyers-par-agglomeration/"
    all_resources = []
    page = 1
    while True:
        r = requests.get(url, params={"page": page, "page_size": 100})
        data = r.json()
        batch = data.get("resources", [])
        if not batch:
            break
        all_resources.extend(batch)
        if len(all_resources) >= data.get("total", 0):
            break
        page += 1
    return [r for r in all_resources if r.get("format", "").lower() == "zip"]


def selectionner_plus_recents(zips: list, obs_cibles: set) -> dict:
    selectionnes = {}
    for res in zips:
        url = res.get("url", "")
        obs_code = extraire_obs_depuis_url(url)
        if obs_code is None or obs_code not in obs_cibles:
            continue
        if obs_code not in selectionnes or \
           res.get("last_modified", "") > selectionnes[obs_code].get("last_modified", ""):
            selectionnes[obs_code] = res
    return selectionnes


def telecharger_zip(obs_code: str, url: str, dest: str):
    if os.path.exists(dest) and os.listdir(dest):
        print(f"[ZONAGES] Déjà présent : {obs_code}")
        return True
    try:
        content = requests.get(url, timeout=60).content
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            z.extractall(dest)
        time.sleep(0.3)
        return True
    except Exception as e:
        print(f"[ZONAGES] Erreur {obs_code} : {e}")
        return False


def ingest_zonages():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("[ZONAGES] Collecte des observatoires cibles...")
    obs_cibles = collecter_observatoires_cibles()
    print(f"[ZONAGES] {len(obs_cibles)} observatoires cibles")

    print("[ZONAGES] Récupération des ZIPs depuis l'API Data.gouv...")
    zips = recuperer_zips_api()
    print(f"[ZONAGES] {len(zips)} ZIPs trouvés")

    selectionnes = selectionner_plus_recents(zips, obs_cibles)
    print(f"[ZONAGES] {len(selectionnes)}/{len(obs_cibles)} observatoires matchés")

    manquants = obs_cibles - set(selectionnes.keys())
    if manquants:
        print(f"[ZONAGES] Non trouvés sur l'API : {sorted(manquants)}")

    ok, erreurs = 0, []
    for i, (obs_code, res) in enumerate(sorted(selectionnes.items())):
        dest = os.path.join(OUT_DIR, obs_code)
        success = telecharger_zip(obs_code, res["url"], dest)
        if success:
            ok += 1
        else:
            erreurs.append(obs_code)

    print(f"[ZONAGES] {ok}/{len(selectionnes)} ZIPs téléchargés")
    if erreurs:
        print(f"[ZONAGES] Erreurs réseau : {erreurs}")


if __name__ == "__main__":
    ingest_zonages()
