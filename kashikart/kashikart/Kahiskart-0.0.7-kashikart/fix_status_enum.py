import sqlite3

db_path = 'tender_dev.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Fix lowercase 'active' to 'ACTIVE'
c.execute("UPDATE sources SET status = 'ACTIVE' WHERE status = 'active';")
fixed_lowercase = c.rowcount
print(f"Fixed {fixed_lowercase} lowercase 'active' to 'ACTIVE'")

# Report all ERROR sources
c.execute("SELECT id, name, status, is_active FROM sources WHERE status = 'ERROR';")
errors = c.fetchall()
print("\nRemaining ERROR sources:")
for row in errors:
    print(row)
print(f"Total ERROR: {len(errors)}")

# Optional: Set ERROR to ACTIVE (uncomment if needed)
# c.execute("UPDATE sources SET status = 'ACTIVE', is_active = 1 WHERE status = 'ERROR';")
# conn.commit()
# print("\nSet all ERROR to ACTIVE")

conn.commit()
conn.close()
print("\nStatus enum fixed - refresh app.")
