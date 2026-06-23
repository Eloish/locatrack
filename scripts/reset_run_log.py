"""
Vide le run_log pour forcer le rechargement de toutes les tables.
Usage :
  python scripts/reset_run_log.py           # vide tout
  python scripts/reset_run_log.py staging   # vide seulement staging.*
  python scripts/reset_run_log.py silver    # vide seulement silver.*
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn

conn = get_conn()
cur = conn.cursor()

schema_filter = sys.argv[1] if len(sys.argv) > 1 else None

if schema_filter:
    cur.execute("DELETE FROM pipeline.run_log WHERE source LIKE %s AND status = 'success'", (f"{schema_filter}.%",))
else:
    cur.execute("DELETE FROM pipeline.run_log WHERE status = 'success'")

conn.commit()
print(f"[RUN_LOG] {cur.rowcount} entrées supprimées" + (f" ({schema_filter}.*)" if schema_filter else " (tout)"))
cur.close()
conn.close()
