import os
import psycopg2
import yaml
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

db = config["database"]
conn = psycopg2.connect(
    host=db['host'], port=db['port'],
    dbname=db['name'], user=db['user'],
    password=db['password']
)
cur = conn.cursor()

# Détecter automatiquement les années depuis les fichiers Bronze
# On prend toutes les années disponibles dans DVF, loyers et INSEE
annees = set()

for source in ["dvf", "loyers", "insee"]:
    dossier = os.path.join(BASE_DIR, f"data/bronze/{source}")
    if os.path.exists(dossier):
        for d in os.listdir(dossier):
            if d.startswith("annee="):
                annee = int(d.split("=")[1])
                annees.add(annee)

annees = sorted(annees)
print(f"Années détectées : {annees}")

for annee in annees:
    cur.execute("""
        INSERT INTO silver.dim_temps (annee)
        VALUES (%s)
        ON CONFLICT (annee) DO NOTHING
    """, (annee,))

conn.commit()
cur.close()
conn.close()

print(f"✅ dim_temps remplie — {len(annees)} années !")