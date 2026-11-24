import os
import shutil
import sqlite3
from datetime import datetime

db_path = r'C:\Users\neera\OneDrive\Desktop\SmartGateAI\backend\storage\smartgate.db'
backup_dir = r'C:\Users\neera\OneDrive\Desktop\SmartGateAI\backend\storage\backups'
os.makedirs(backup_dir, exist_ok=True)

# 1. Backup DB
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_path = os.path.join(backup_dir, f'smartgate_backup_{timestamp}.db')
shutil.copy2(db_path, backup_path)
print(f'Database backup created successfully: {backup_path}')

# 2. Check and migrate
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM students')
print('Existing students before migration:', cur.fetchone()[0])

cur.execute('PRAGMA table_info(students)')
existing_cols = [c[1] for c in cur.fetchall()]
print('Existing columns:', existing_cols)

columns_to_add = [
    ('category', "VARCHAR(20) DEFAULT 'Day Scholar' NOT NULL"),
    ('hostel_name', 'VARCHAR(100) NULL'),
    ('hostel_block', 'VARCHAR(50) NULL'),
    ('room_number', 'VARCHAR(50) NULL')
]

for col_name, col_def in columns_to_add:
    if col_name not in existing_cols:
        sql = f'ALTER TABLE students ADD COLUMN {col_name} {col_def}'
        cur.execute(sql)
        print(f'Added column {col_name} to students table.')
    else:
        print(f'Column {col_name} already exists in students table.')

conn.commit()

# Verify
cur.execute('PRAGMA table_info(students)')
print('Updated students columns:', [c[1] for c in cur.fetchall()])
cur.execute('SELECT student_id, full_name, category, hostel_name FROM students')
print('Students verification:', cur.fetchall())

conn.close()
print('Migration step 1 complete!')
