import sqlite3
import sys
sys.path.append('.')

conn = sqlite3.connect('tender_dev.db')
c = conn.cursor()

print("Sample tenders source_url check:")
c.execute('SELECT id, title, source_id, source_url FROM tenders WHERE source_url IS NOT NULL LIMIT 5')
with_url = c.fetchall()
print("With URL:", with_url)

c.execute('SELECT COUNT(*) FROM tenders WHERE source_url IS NULL')
null_count = c.fetchone()[0]
print(f"Tenders with NULL source_url: {null_count}")

c.execute('SELECT COUNT(*) FROM tenders')
total_count = c.fetchone()[0]
print(f"Total tenders: {total_count}")

c.execute('SELECT DISTINCT s.name, COUNT(t.id) FROM sources s LEFT JOIN tenders t ON t.source_id = s.id GROUP BY s.id')
sources = c.fetchall()
print("\nSources and tender counts:")
for source in sources:
    print(source)

conn.close()
print("\nUse: python check_tender_urls.py")

