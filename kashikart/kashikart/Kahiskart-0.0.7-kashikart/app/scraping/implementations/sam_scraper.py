from playwright.sync_api import sync_playwright
from typing import List, Dict
from app.models.source import Source

class SamGovScraper:

    @staticmethod
    def scrape_opportunities(source: Source, keyword: str = "IT software tender") -> List[Dict]:

        results: List[Dict] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            print("Opening SAM.gov...")
            page.goto("https://sam.gov/opportunities", timeout=60000)

            page.wait_for_timeout(12000)

            print("Clicking search box...")
            page.get_by_role("textbox").first.click()

            print(f"Typing: {keyword}")
            page.keyboard.type(keyword, delay=80)
            page.keyboard.press("Enter")

            print("Waiting for results...")

            # CRITICAL — correct selector
            page.wait_for_selector("div[data-testid='opportunity-card']", timeout=40000)

            cards = page.locator("div[data-testid='opportunity-card']").all()

            print(f"Found raw cards: {len(cards)}")

            for i, card in enumerate(cards[:10]):  
                try:
                    title = card.locator("h3").inner_text(timeout=5000)

                    notice_id = card.locator("span:has-text('Notice ID')").inner_text()

                    deadline = card.locator("span:has-text('Response Date')").inner_text()

                    results.append({
                        "reference_id": notice_id.replace("Notice ID:", "").strip(),
                        "title": title.strip(),
                        "description": f"Scraped from SAM.gov for keyword: {keyword}",
                        "deadline_date": deadline.replace("Response Date:", "").strip(),
                        "status": "open"
                    })

                except Exception as e:
                    print(f"Skipping one card: {e}")

            browser.close()

        print(f"Scraped {len(results)} tenders")
        return results
