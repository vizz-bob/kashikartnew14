import sqlite3

conn = sqlite3.connect('tender_dev.db')
c = conn.cursor()

# Get sources with urls
c.execute('SELECT id, name, url FROM sources WHERE url IS NOT NULL LIMIT 10')
sources = c.fetchall()
print("Available sources:", sources)

# Update tenders with source base URL if no source_url
c.execute("""
UPDATE tenders 
SET source_url = (
    SELECT s.url FROM sources s WHERE s.id = tenders.source_id
)
WHERE source_url IS NULL AND source_id IS NOT NULL
""")

updated = c.rowcount
conn.commit()
print(f"Updated {updated} tenders with source base URLs")

# Sample check
c.execute('SELECT id, title, source_url FROM tenders WHERE source_url IS NOT NULL LIMIT 3')
print("Sample updated tenders:")
for row in c.fetchall():
    print(row)

conn.close()
print("Run: cd kashikart/Kahiskart-0.0.7-kashikart && venv\\Scripts\\activate && python fix_tender_urls.py")

