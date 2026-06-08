import os
import psycopg2
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

db = config["database"]
conn = psycopg2.connect(
    host=db["host"],
    port=db["port"],
    dbname=db["name"],
    user=db["user"],
    password=db["password"]
)
cur = conn.cursor()

# Créer la table si elle n'existe pas encore
cur.execute("""
CREATE TABLE IF NOT EXISTS silver.dim_temps (
    annee INTEGER PRIMARY KEY
)
""")
conn.commit()

# Rechercher les années disponibles dans les dossiers Bronze
annees = set()
for source in ["dvf", "loyers", "insee"]:
    source_dir = os.path.join(BASE_DIR, "data", "bronze", source)
    if not os.path.isdir(source_dir):
        continue
    for entry in os.listdir(source_dir):
        if entry.startswith("annee="):
            try:
                annees.add(int(entry.split("=", 1)[1]))
            except ValueError:
                continue

if not annees:
    raise SystemExit("Aucune année détectée dans data/bronze. Vérifie les dossiers dvf, loyers et insee.")

annees = sorted(annees)
print(f"Années détectées : {annees}")

for annee in annees:
    cur.execute(
        """
        INSERT INTO silver.dim_temps (annee)
        VALUES (%s)
        ON CONFLICT (annee) DO NOTHING
        """,
        (annee,)
    )

conn.commit()
cur.close()
conn.close()

print(f"✅ silver.dim_temps rempli avec {len(annees)} années.")
