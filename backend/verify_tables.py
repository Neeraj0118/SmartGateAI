import sys
import os
backend_dir = r'C:\Users\neera\OneDrive\Desktop\SmartGateAI\backend'
sys.path.insert(0, backend_dir)
os.environ['SMARTGATE_ADMIN_API_KEY'] = 'verify_key'

from app.db.session import engine, init_db
import app.models  # load all models
init_db()

import sqlite3
conn = sqlite3.connect(os.path.join(backend_dir, 'storage', 'smartgate.db'))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('All database tables:', tables)
assert 'hostel_permissions' in tables, 'hostel_permissions table missing'
assert 'active_outings' in tables, 'active_outings table missing'
assert 'security_alerts' in tables, 'security_alerts table missing'
conn.close()
print('New tables verified successfully!')
