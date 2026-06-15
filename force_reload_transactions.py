# dans un fichier force_reload_transactions.py temporaire
import sys; sys.path.insert(0, '.')
from utils.db import get_conn
from utils.loader import force_reload

conn = get_conn()
force_reload(conn, 'silver', 'fact_transactions')
conn.commit()
conn.close()
print("Done")