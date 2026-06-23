"""
Script de bootstrap à lancer UNE SEULE FOIS sur un environnement
qui a déjà des données en base (staging et/ou silver).

Il scanne toutes les tables existantes et les marque 'success'
dans le run_log — le pipeline les skipera au prochain lancement.
"""

import psycopg2
from utils.db import get_conn
from utils.run_log import ensure_run_log_table, is_already_done, log_start, log_success


def get_tables_with_data(conn, schema: str) -> list[str]:
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """, (schema,))
    tables = [row[0] for row in cur.fetchall()]
    cur.close()

    non_vides = []
    for table in tables:
        cur = conn.cursor()
        try:
            cur.execute(f'SELECT EXISTS (SELECT 1 FROM {schema}."{table}" LIMIT 1)')
            if cur.fetchone()[0]:
                non_vides.append(table)
        except Exception:
            pass
        finally:
            cur.close()
    return non_vides


def bootstrap_schema(conn, schema: str):
    tables = get_tables_with_data(conn, schema)
    print(f"\n[BOOTSTRAP] {schema} — {len(tables)} tables avec données")

    for table in tables:
        source = f"{schema}.{table}"
        if is_already_done(conn, source):
            print(f"  déjà dans le run_log : {source}")
            continue
        run_id = log_start(conn, source)

        cur = conn.cursor()
        cur.execute(f'SELECT COUNT(*) FROM {schema}."{table}"')
        nb = cur.fetchone()[0]
        cur.close()

        log_success(conn, run_id, nb)
        print(f"  marqué success : {source} ({nb} lignes)")


def main():
    conn = get_conn()
    ensure_run_log_table(conn)

    bootstrap_schema(conn, "staging")
    bootstrap_schema(conn, "silver")

    conn.close()
    print("\n[BOOTSTRAP] Terminé — le pipeline skipera les tables existantes")


if __name__ == "__main__":
    main()
