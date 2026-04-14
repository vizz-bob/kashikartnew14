from playwright.async_api import async_playwright
from typing import List, Dict
from app.scraping.base.scraper import BaseScraper
from app.utils.encryption import encryption_service


class LoginScraper(BaseScraper):
    async def scrape(self) -> List[Dict]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await self._login(page)
                return await self.extract_from_page(page)
            finally:
                await browser.close()

    async def _login(self, page):
        username = self.source.username
        password = encryption_service.decrypt(self.source.encrypted_password)

        await page.goto(self.source.login_url)
        await page.fill('input[name="username"]', username)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state('networkidle')

    async def extract_from_page(self, page) -> List[Dict]:
        """
        MUST be implemented in child class
        """
        raise NotImplementedError
