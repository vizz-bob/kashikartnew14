from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
from app.scraping.base.scraper import BaseScraper
from app.utils.logger import setup_logger
from app.utils.encryption import encryption_service

logger = setup_logger("portal_scraper", log_file="logs/portal_scraper.log")


class PortalScraper(BaseScraper):
    """
    Scraper for login-protected portals and JavaScript-rendered sites.
    Uses Selenium WebDriver for browser automation.
    """

    def __init__(self, source_config: Dict):
        super().__init__(source_config)
        self.driver = None
        self.wait_timeout = 10

    async def fetch_data(self) -> List[Dict]:
        """Fetch tenders from protected portal"""
        all_tenders = []

        try:
            # Setup Selenium WebDriver
            self._setup_driver()

            # Login if required
            if self.requires_login:
                login_success = await self._login()
                if not login_success:
                    logger.error("Login failed, aborting fetch")
                    return all_tenders

            # Navigate to tender listing page
            self.driver.get(self.url)
            self._wait_for_page_load()

            # Fetch multiple pages
            for page in range(1, self.max_pages + 1):
                logger.info(f"Fetching page {page}")

                # Wait for content to load
                self._wait_for_page_load()

                # Get page source and parse
                page_source = self.driver.page_source
                tenders = self.parse_page(page_source)

                if not tenders:
                    logger.info("No more tenders found, stopping pagination")
                    break

                # Normalize and add tenders
                for tender_data in tenders:
                    normalized = self.normalize_tender(tender_data)
                    all_tenders.append(normalized)

                logger.info(f"Found {len(tenders)} tenders on page {page}")

                # Try to go to next page
                if page < self.max_pages:
                    next_page_success = self._go_to_next_page()
                    if not next_page_success:
                        logger.info("No next page available")
                        break

                # Be polite, wait between requests
                time.sleep(2)

        finally:
            # Always close the driver
            if self.driver:
                self.driver.quit()

        return all_tenders

    def parse_page(self, content: str) -> List[Dict]:
        """Parse HTML content from portal"""
        soup = BeautifulSoup(content, 'lxml')
        tenders = []

        # Get parsing rules from config
        rules = self.source_config.get('parsing_rules', {})

        # Find tender containers
        container_selector = rules.get('container_selector', 'div.tender-row, tr.tender-item')
        tender_elements = soup.select(container_selector)

        logger.info(f"Found {len(tender_elements)} tender elements")

        for element in tender_elements:
            try:
                tender = self._parse_tender_element(element, rules)
                if tender and tender.get('title'):
                    tenders.append(tender)
            except Exception as e:
                logger.error(f"Error parsing tender element: {e}")
                continue

        return tenders

    def _parse_tender_element(self, element, rules: Dict) -> Dict:
        """Parse individual tender element"""
        tender = {}

        # Title
        title_selector = rules.get('title_selector', 'h3, .title, td:nth-child(2)')
        title_elem = element.select_one(title_selector)
        tender['title'] = title_elem.get_text(strip=True) if title_elem else ''

        # Description
        desc_selector = rules.get('description_selector', 'p, .description')
        desc_elem = element.select_one(desc_selector)
        tender['description'] = desc_elem.get_text(strip=True) if desc_elem else ''

        # Agency
        agency_selector = rules.get('agency_selector', '.agency, td:nth-child(3)')
        agency_elem = element.select_one(agency_selector)
        tender['agency'] = agency_elem.get_text(strip=True) if agency_elem else ''

        # Reference ID
        ref_selector = rules.get('reference_selector', '.reference, .id, td:nth-child(1)')
        ref_elem = element.select_one(ref_selector)
        tender['reference_id'] = ref_elem.get_text(strip=True) if ref_elem else ''

        # Dates
        date_selector = rules.get('date_selector', '.date, .posted')
        date_elem = element.select_one(date_selector)
        tender['publish_date'] = date_elem.get_text(strip=True) if date_elem else ''

        deadline_selector = rules.get('deadline_selector', '.deadline, .due-date')
        deadline_elem = element.select_one(deadline_selector)
        tender['deadline'] = deadline_elem.get_text(strip=True) if deadline_elem else ''

        # URL
        link_elem = element.select_one('a')
        if link_elem and link_elem.get('href'):
            tender['url'] = self._make_absolute_url(link_elem['href'])

        # Location
        location_selector = rules.get('location_selector', '.location')
        location_elem = element.select_one(location_selector)
        tender['location'] = location_elem.get_text(strip=True) if location_elem else ''

        return tender

    def _setup_driver(self):
        """Setup Selenium WebDriver with options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    async def _login(self) -> bool:
        """Perform login to portal"""
        try:
            username = self.source_config.get('username')
            password_encrypted = self.source_config.get('password')

            if not username or not password_encrypted:
                logger.error("Missing login credentials")
                return False

            # Decrypt password
            password = encryption_service.decrypt(password_encrypted)

            # Navigate to login page (assuming login URL is base URL)
            login_url = self.url.rsplit('/', 1)[0] + '/login'
            self.driver.get(login_url)

            # Wait for login form
            wait = WebDriverWait(self.driver, self.wait_timeout)

            # Find and fill username field
            username_field = wait.until(
                EC.presence_of_element_located((By.NAME, 'username'))
            )
            username_field.send_keys(username)

            # Find and fill password field
            password_field = self.driver.find_element(By.NAME, 'password')
            password_field.send_keys(password)

            # Find and click submit button
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
            submit_button.click()

            # Wait for redirect after login
            time.sleep(3)

            # Check if login was successful (you may need to customize this)
            if 'login' not in self.driver.current_url.lower():
                logger.info("Login successful")
                return True
            else:
                logger.error("Login failed - still on login page")
                return False

        except TimeoutException:
            logger.error("Login form elements not found - timeout")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def _wait_for_page_load(self):
        """Wait for page to fully load"""
        try:
            wait = WebDriverWait(self.driver, self.wait_timeout)
            wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            time.sleep(1)  # Additional wait for dynamic content
        except TimeoutException:
            logger.warning("Page load timeout")

    def _go_to_next_page(self) -> bool:
        """Navigate to next page"""
        try:
            # Try to find and click "Next" button
            next_selectors = [
                'a.next',
                'a[rel="next"]',
                '.pagination .next',
                'button.next-page',
                'a:contains("Next")'
            ]

            for selector in next_selectors:
                try:
                    # Handle CSS selectors
                    if not selector.startswith('a:contains'):
                        next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    else:
                        # For "Next" text, use XPath
                        next_button = self.driver.find_element(
                            By.XPATH,
                            "//a[contains(text(), 'Next')] | //button[contains(text(), 'Next')]"
                        )

                    if next_button.is_displayed() and next_button.is_enabled():
                        next_button.click()
                        time.sleep(2)  # Wait for page load
                        return True
                except NoSuchElementException:
                    continue

            return False

        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False

    def _make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute"""
        if url.startswith('http'):
            return url

        from urllib.parse import urljoin
        return urljoin(self.driver.current_url, url)

    def close(self):
        """Close WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")