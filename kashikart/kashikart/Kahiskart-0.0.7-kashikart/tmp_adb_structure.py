import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
response = scraper.get('https://www.adb.org/projects/tenders/procurement-notices')

soup = BeautifulSoup(response.text, 'html.parser')
print('Title:', soup.title.string if soup.title else 'No Title')

# Look for standard list items
items = soup.select('.item')
rows = soup.select('tr')
views = soup.select('[class*="view"]')

print(f'Items found (.item): {len(items)}')
print(f'Rows found (tr): {len(rows)}')
print(f'Views elements found: {len(views)}')

# Let's save the HTML to parse it manually if needed
with open('tmp_adb.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
