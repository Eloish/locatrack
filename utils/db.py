import psycopg2
from sqlalchemy import create_engine
from utils.config import load_config


def _db_config() -> dict:
    import os
    cfg = load_config()["database"]
    # Variables d'environnement Docker en priorite sur config.yml
    return {
        "host":     os.environ.get("DB_HOST",     cfg["host"]),
        "port":     os.environ.get("DB_PORT",     str(cfg["port"])),
        "name":     os.environ.get("DB_NAME",     cfg["name"]),
        "user":     os.environ.get("DB_USER",     cfg["user"]),
        "password": os.environ.get("DB_PASSWORD", cfg["password"]),
    }


def get_engine():
    db = _db_config()
    return create_engine(
        f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}",
        connect_args={
            "options": "-c statement_timeout=0",
            "keepalives": 1,
            "keepalives_idle": 60,
            "keepalives_interval": 10,
            "keepalives_count": 6,
        },
    )


def get_conn():
    db = _db_config()
    return psycopg2.connect(
        host=db["host"],
        port=db["port"],
        dbname=db["name"],
        user=db["user"],
        password=db["password"],
        options="-c statement_timeout=0",
        keepalives=1,
        keepalives_idle=60,
        keepalives_interval=10,
        keepalives_count=6,
    )
