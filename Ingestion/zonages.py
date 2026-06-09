import requests, zipfile, io, os, time, re
import glob
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR  = os.path.join(BASE_DIR, "data/bronze/loyers_zonages")
os.makedirs(OUT_DIR, exist_ok=True)

# ── 1. Observatoires cibles depuis TOUS les parquets de loyers ────────────────
print("🔍 Recherche de tous les observatoires uniques dans l'historique des loyers...")

# On scanne dynamiquement tout le sous-dossier "loyers" à la recherche des fichiers .parquet
DOSSIER_LOYERS = os.path.join(BASE_DIR, "data/bronze/loyers")
fichiers_loyers = glob.glob(os.path.join(DOSSIER_LOYERS, "**", "*.parquet"), recursive=True)

obs_cibles = set()

if not fichiers_loyers:
    print(f"❌ Aucun fichier Parquet trouvé dans {DOSSIER_LOYERS}. Vérifie tes dossiers.")
    exit()

for f in fichiers_loyers:
    try:
        # On lit uniquement la colonne Observatory pour optimiser la mémoire et la vitesse
        df_temp = pd.read_parquet(f, columns=["Observatory"])
        obs_cibles.update(df_temp["Observatory"].dropna().unique())
    except Exception as e:
        print(f"  ⚠ Impossible de lire le fichier {os.path.basename(f)} : {e}")

print(f"✓ {len(obs_cibles)} observatoires cibles uniques trouvés au total (Objectif : 44)\n")

# ── 2. Récupérer toutes les ressources via l'API ──────────────────────────────
DATASET_URL = "https://www.data.gouv.fr/api/1/datasets/resultats-des-observatoires-locaux-des-loyers-par-agglomeration/"

all_resources = []
page = 1
while True:
    r = requests.get(DATASET_URL, params={"page": page, "page_size": 100})
    data = r.json()
    batch = data.get("resources", [])
    if not batch:
        break
    all_resources.extend(batch)
    if len(all_resources) >= data.get("total", 0):
        break
    page += 1

zips = [r for r in all_resources if r.get("format", "").lower() == "zip"]
print(f"✓ {len(zips)} ZIP trouvés sur l'API Data.gouv\n")

# ── 3. Extraire le code observatoire depuis l'URL ─────────────────────────────
def extraire_obs_depuis_url(url: str) -> str | None:
    """
    'https://.../Base_OP_2025_L3400.zip' → 'B3400'
    'https://.../Base_OP_2024_L2A00.zip' → 'B2A00'
    'https://.../Base_OP_2024_L2B00.zip' → 'B2B00'
    """
    match = re.search(r'_L(\d{1,2}[AB]\d{2}|\d{4})\.zip', url, re.IGNORECASE)
    if match:
        return "B" + match.group(1).upper()
    return None

# ── 4. Garder uniquement le plus récent par observatoire ─────────────────────
selectionnes = {}  # obs_code → ressource la plus récente

for res in zips:
    url = res.get("url", "")
    obs_code = extraire_obs_depuis_url(url)

    if obs_code is None:
        continue
    if obs_code not in obs_cibles:
        continue

    # Garder le plus récent
    if obs_code not in selectionnes or \
       res.get("last_modified", "") > selectionnes[obs_code].get("last_modified", ""):
        selectionnes[obs_code] = res

print(f"✓ {len(selectionnes)}/{len(obs_cibles)} observatoires matchés avec l'API\n")

manquants = obs_cibles - set(selectionnes.keys())
if manquants:
    print(f"⚠ Non trouvés sur l'API : {sorted(manquants)}\n")

# ── 5. Télécharger uniquement les ZIP utiles ──────────────────────────────────
ok, erreurs = 0, []

for i, (obs_code, res) in enumerate(sorted(selectionnes.items())):
    dest = os.path.join(OUT_DIR, obs_code)

    if os.path.exists(dest) and os.listdir(dest):
        print(f"[{i+1}/{len(selectionnes)}] ✓ Déjà présent localement : {obs_code}")
        ok += 1
        continue

    print(f"[{i+1}/{len(selectionnes)}] ⬇ {obs_code} — {res['url']}")
    try:
        content = requests.get(res["url"], timeout=60).content
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            z.extractall(dest)
        ok += 1
        time.sleep(0.3)
    except Exception as e:
        print(f"   ⚠ Erreur : {e}")
        erreurs.append(obs_code)

# ── 6. Rapport final ──────────────────────────────────────────────────────────
print(f"\n{'─'*50}")
print(f"✅ {ok}/{len(selectionnes)} ZIP téléchargés et extraits")

manquants_final = obs_cibles - set(selectionnes.keys())
if manquants_final:
    print(f"⚠ Observatoires non couverts : {sorted(manquants_final)}")
else:
    print(f"✓ Tous les {len(obs_cibles)} observatoires de l'historique sont couverts")

if erreurs:
    print(f"⚠ Erreurs réseau : {erreurs}")
for res in zips:
    obs_code = extraire_obs_depuis_url(res.get("url", ""))
    if obs_code in selectionnes:
        print(obs_code, "|", res.get("title"))