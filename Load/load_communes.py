import os
import pandas as pd
import psycopg2
from io import StringIO
from sqlalchemy import create_engine
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config.yml")

with open(config_path) as f:
    config = yaml.safe_load(f)

db = config["database"]
engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
)

def load_to_staging(df, table_name):
    print(f"Chargement de {table_name} via COPY...")
    df.columns = [col.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "") for col in df.columns]
    df.head(0).to_sql(table_name, engine, schema="staging", if_exists="replace", index=False)
    conn = psycopg2.connect(host=db['host'], port=db['port'], dbname=db['name'], user=db['user'], password=db['password'])
    cur = conn.cursor()
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="")
    buffer.seek(0)
    cur.copy_expert(f"COPY staging.{table_name} FROM STDIN WITH (FORMAT CSV, NULL '')", buffer)
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ {table_name} chargé — {len(df)} lignes")

print("--- Chargement Communes dans staging ---")
path = os.path.join(BASE_DIR, "data/bronze/communes/communes.parquet")
df = pd.read_parquet(path)
load_to_staging(df, "communes")

print("\n✅ Communes staging terminé !")