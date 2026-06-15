"""
Gestion du run_log pour l'idempotence du pipeline.

Table pipeline.run_log :
  - source      : identifiant unique du run (ex: "staging.dvf_2023", "silver.fact_transactions")
  - status      : "running" | "success" | "error"
  - rows_loaded : nombre de lignes insérées
  - started_at  : timestamp de début
  - finished_at : timestamp de fin
  - error_msg   : message d'erreur si status = "error"

Logique d'idempotence :
  - Si source a déjà un run "success" → on skip
  - Si source a un run "running" → run précédent planté → on réessaie
  - Si source a un run "error" → on réessaie
"""

from datetime import datetime


def ensure_run_log_table(conn):
    cur = conn.cursor()
    try:
        cur.execute("CREATE SCHEMA IF NOT EXISTS pipeline")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pipeline.run_log (
                id          SERIAL PRIMARY KEY,
                source      VARCHAR(200) NOT NULL,
                status      VARCHAR(20)  NOT NULL,
                rows_loaded INTEGER,
                started_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMP,
                error_msg   TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_log_source_status
            ON pipeline.run_log (source, status)
        """)
        conn.commit()
    finally:
        cur.close()


def is_already_done(conn, source: str) -> bool:
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 1 FROM pipeline.run_log
            WHERE source = %s AND status = 'success'
            LIMIT 1
        """, (source,))
        return cur.fetchone() is not None
    finally:
        cur.close()


def log_start(conn, source: str) -> int:
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO pipeline.run_log (source, status, started_at)
            VALUES (%s, 'running', %s)
            RETURNING id
        """, (source, datetime.now()))
        run_id = cur.fetchone()[0]
        conn.commit()
        return run_id
    finally:
        cur.close()


def log_success(conn, run_id: int, rows_loaded: int):
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE pipeline.run_log
            SET status = 'success', rows_loaded = %s, finished_at = %s
            WHERE id = %s
        """, (rows_loaded, datetime.now(), run_id))
        conn.commit()
    finally:
        cur.close()


def log_error(conn, run_id: int, error_msg: str):
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE pipeline.run_log
            SET status = 'error', finished_at = %s, error_msg = %s
            WHERE id = %s
        """, (datetime.now(), str(error_msg), run_id))
        conn.commit()
    finally:
        cur.close()
