import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import create_engine, text
from utils.config import load_config

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        config = load_config()
        db = config["database"]
        host = os.environ.get("DB_HOST", db["host"])
        port = os.environ.get("DB_PORT", db["port"])
        user = os.environ.get("DB_USER", db["user"])
        password = os.environ.get("DB_PASSWORD", db["password"])
        name = os.environ.get("DB_NAME", db["name"])
        _engine = create_engine(
            f"postgresql://{user}:{password}@{host}:{port}/{name}"
        )
    return _engine


def query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)