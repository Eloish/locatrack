"""
Usage : python scripts/force_reload.py <schema> <table>
Exemples :
  python scripts/force_reload.py silver dim_commune
  python scripts/force_reload.py silver fact_transactions
  python scripts/force_reload.py staging dvf_2024
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn
from utils.loader import force_reload

if len(sys.argv) != 3:
    print("Usage: python scripts/force_reload.py <schema> <table>")
    sys.exit(1)

schema, table = sys.argv[1], sys.argv[2]
conn = get_conn()
force_reload(conn, schema, table)
conn.close()
