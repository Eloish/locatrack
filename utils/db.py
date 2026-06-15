import psycopg2
from sqlalchemy import create_engine
from utils.config import load_config


def _db_config() -> dict:
    return load_config()["database"]


def get_engine():
    db = _db_config()
    return create_engine(
        f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
    )


def get_conn():
    db = _db_config()
    return psycopg2.connect(
        host=db["host"],
        port=db["port"],
        dbname=db["name"],
        user=db["user"],
        password=db["password"],
    )
