import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import create_engine
from utils.config import load_config

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        config = load_config()
        db = config["database"]
        _engine = create_engine(
            f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
        )
    return _engine


def query(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, get_engine())