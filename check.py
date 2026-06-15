import sys; sys.path.insert(0, '.')
from utils.db import get_engine
import sqlalchemy as sa

engine = get_engine()
with engine.connect() as conn:
    rows = conn.execute(sa.text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='staging' AND table_name LIKE 'dvf%' ORDER BY table_name"
    )).fetchall()
    print([r[0] for r in rows])