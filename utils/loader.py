from io import StringIO
import pandas as pd
from utils.run_log import ensure_run_log_table, is_already_done, log_start, log_success, log_error


def copy_to_postgres(conn, df: pd.DataFrame, schema: str, table: str, columns: list[str]):
    """
    Charge un DataFrame dans une table silver via TRUNCATE + COPY.
    - Idempotent : skip si un run 'success' existe déjà pour cette table.
    - Atomique   : TRUNCATE + COPY dans une seule transaction, rollback sur erreur.
    """
    source = f"{schema}.{table}"
    ensure_run_log_table(conn)

    if is_already_done(conn, source):
        print(f"[LOADER] {source} déjà chargé (run_log success) — skip")
        return

    run_id = log_start(conn, source)
    cur = conn.cursor()
    try:
        cur.execute(f"TRUNCATE TABLE {source} CASCADE")
        buffer = StringIO()
        df[columns].to_csv(buffer, index=False, header=False, na_rep="")
        buffer.seek(0)
        cur.copy_expert(
            f"COPY {source} ({', '.join(columns)}) FROM STDIN WITH (FORMAT CSV, NULL '')",
            buffer,
        )
        conn.commit()
        log_success(conn, run_id, len(df))
        print(f"[LOADER] {source} — {len(df)} lignes insérées")
    except Exception as e:
        conn.rollback()
        log_error(conn, run_id, str(e))
        print(f"[LOADER] Erreur {source} : {e}")
        raise
    finally:
        cur.close()


def upsert_to_staging(engine, df: pd.DataFrame, table: str, schema: str = "staging"):
    """
    Charge un DataFrame dans une table staging via DROP/CREATE + COPY.
    - Idempotent : skip si un run 'success' existe déjà dans le run_log.
    - Atomique   : COPY dans une transaction, rollback sur erreur.
    """
    from utils.db import get_conn

    source = f"{schema}.{table}"
    conn = get_conn()
    ensure_run_log_table(conn)

    if is_already_done(conn, source):
        print(f"[LOADER] {source} déjà chargé (run_log success) — skip")
        conn.close()
        return

    run_id = log_start(conn, source)

    try:
        df.head(0).to_sql(table, engine, schema=schema, if_exists="replace", index=False)

        cur = conn.cursor()
        try:
            buffer = StringIO()
            df.to_csv(buffer, index=False, header=False, na_rep="")
            buffer.seek(0)
            cur.copy_expert(
                f"COPY {source} FROM STDIN WITH (FORMAT CSV, NULL '')",
                buffer,
            )
            conn.commit()
            log_success(conn, run_id, len(df))
            print(f"[LOADER] {source} — {len(df)} lignes chargées")
        except Exception as e:
            conn.rollback()
            log_error(conn, run_id, str(e))
            print(f"[LOADER] Erreur {source} : {e}")
            raise
        finally:
            cur.close()
    finally:
        conn.close()


def force_reload(conn, schema: str, table: str):
    """
    Supprime l'entrée 'success' du run_log pour forcer un rechargement au prochain run.
    Utile pour rejouer une table sans relancer tout le pipeline.
    """
    source = f"{schema}.{table}"
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM pipeline.run_log WHERE source = %s AND status = 'success'",
            (source,)
        )
        conn.commit()
        print(f"[LOADER] run_log effacé pour {source} — sera rechargé au prochain run")
    finally:
        cur.close()
