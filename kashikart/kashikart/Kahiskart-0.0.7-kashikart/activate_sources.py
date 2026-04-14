import sqlite3
from datetime import datetime

db_path = 'tender_dev.db'

print("Before:")
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('SELECT id, name, status, is_active FROM sources WHERE status=\"ERROR\" OR is_active=0;')
problematic = c.fetchall()
print("Problematic sources:")
for row in problematic:
    print(row)
print(f"Total problematic: {len(problematic)}")

# Update
status="ACTIVE"
updated = c.rowcount
conn.commit()

# After
c.execute('SELECT id, name, status, is_active FROM sources WHERE status=\"ERROR\" OR is_active=0;')
after = c.fetchall()
conn.close()

print(f"\nUpdated {updated} sources to active status.")
print("Remaining problematic:", len(after))
print("Done - refresh sources page.")
