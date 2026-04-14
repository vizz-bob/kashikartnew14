from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from typing import List, Dict
from app.models.source import Source
import time


class SamGovAPIScraper:

    @staticmethod
    def scrape_opportunities(
        source: Source,
        keyword: str = "IT software tender"
    ) -> List[Dict]:

        results: List[Dict] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            print("Opening SAM.gov...")
            page.goto("https://sam.gov/opportunities", timeout=60000)

            # Wait for page to settle
            page.wait_for_timeout(12000)

            print("Clicking search box...")
            try:
                search_box = page.get_by_role("textbox").first
                search_box.click(timeout=5000)
            except PlaywrightTimeout:
                print("Search box not found immediately — retrying via keyboard...")
                page.keyboard.press("Tab")
                page.keyboard.press("Tab")

            print(f"Typing keyword: {keyword}")
            page.keyboard.type(keyword, delay=80)
            page.keyboard.press("Enter")

            print("Waiting for results to load...")
            page.wait_for_timeout(20000)  # SAM is slow — keep this

            # Correct selector for SAM.gov result cards
            cards = page.locator("div[data-testid='search-result-card']").all()

            print(f"Found result cards: {len(cards)}")

            for i, card in enumerate(cards[:10]):  # limit to first 10 for now
                try:
                    # ---- TITLE ----
                    title = card.locator("a").first.inner_text(timeout=5000)

                    # ---- NOTICE ID ----
                    notice_id = "UNKNOWN"
                    try:
                        notice_id = (
                            card.locator("text=Notice ID")
                            .first
                            .inner_text(timeout=3000)
                            .replace("Notice ID:", "")
                            .strip()
                        )
                    except:
                        notice_id = f"UNKNOWN-{i}"

                    # ---- RESPONSE DATE ----
                    deadline = "Not specified"
                    try:
                        deadline = (
                            card.locator("text=Response Date")
                            .first
                            .inner_text(timeout=3000)
                            .replace("Response Date:", "")
                            .strip()
                        )
                    except:
                        pass

                    tender = {
                        "reference_id": notice_id,
                        "title": title.strip(),
                        "description": f"Scraped from SAM.gov for keyword: {keyword}",
                        "deadline_date": deadline,
                        "status": "open",
                        "source_url": "https://sam.gov/opportunities"
                    }

                    results.append(tender)

                except Exception as e:
                    print(f"Skipping one card due to error: {e}")

            browser.close()

        print(f"Scraped {len(results)} tenders from SAM.gov")
        return results
