import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import os

def test_adb():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    
    driver = uc.Chrome(options=options)
    try:
        url = "https://www.adb.org/projects/procurement"
        print(f"Navigating to {url}")
        driver.get(url)
        time.sleep(10)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Save for debug
        with open("adb_test_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        print(f"Page title: {driver.title}")
        
        # Check for container .item
        items = soup.select(".item")
        print(f"Found {len(items)} elements with selector '.item'")
        
        if len(items) == 0:
            # Try to find common list item selectors
            common_selectors = [".views-row", ".list-item", "article", ".node-teaser"]
            for sel in common_selectors:
                elements = soup.select(sel)
                if elements:
                    print(f"Found {len(elements)} elements with selector '{sel}'")
        else:
            # Show first item title
            title_sel = ".item-title a, .title a"
            first_title = items[0].select_one(title_sel)
            if first_title:
                print(f"First item title: {first_title.get_text(strip=True)}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_adb()
