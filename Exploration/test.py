from sqlalchemy import create_engine, text
import yaml, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "config.yml")) as f:
    config = yaml.safe_load(f)

db = config["database"]
engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@"
    f"{db['host']}:{db['port']}/{db['name']}"
)

with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS staging.zonage_brut"))
    conn.commit()

print("✅ staging.zonage_brut supprimée")