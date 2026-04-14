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
from app.models.source import Source
from app.utils.logger import setup_logger
from app.utils.encryption import encryption_service
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc

logger = setup_logger("portal_scraper", log_file="logs/portal_scraper.log")


class PortalScraper(BaseScraper):
    """
    Scraper for login-protected portals and JavaScript-rendered sites.
    Uses Selenium WebDriver for browser automation.
    """

    def __init__(self, source: Source):
        super().__init__(source)
        self.driver = None
        self.wait_timeout = 10
        self.max_pages = 5 # Default
        self.requires_login = source.login_type == "required"

    async def scrape(self) -> List[Dict]:
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
                    raise Exception("Login failed")

            # Navigate to tender listing page
            self.driver.get(self.source.url)
            self._wait_for_page_load()

            # Fetch multiple pages
            for page in range(1, self.max_pages + 1):
                logger.info(f"Fetching page {page}")

                # Wait for content to load and potential Cloudflare redirect
                self._wait_for_page_load()
                
                # Scroll a bit to trigger lazy loads and appear more human
                self.driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)

                # Get page source and parse
                page_source = self.driver.page_source
                tenders = self.parse_page(page_source)

                if not tenders:
                    logger.info("No more tenders found, stopping pagination")
                    # Debug: Save page source to see what it looks like
                    with open(f"logs/debug_page_{page}.html", "w", encoding="utf-8") as f:
                        f.write(page_source)
                    break

                # Normalize and add tenders
                for tender_data in tenders:
                    tender_data['source_id'] = self.source.id
                    tender_data['source_url'] = self.source.url
                    all_tenders.append(tender_data)

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
        soup = BeautifulSoup(content, 'html.parser')
        tenders = []

        # Get parsing rules from config
        config = self._normalize_config(self.source.selector_config or {})
        container_selector = config.get("container_selector")
        
        if not container_selector:
            logger.warning(f"No container selector for portal {self.source.name}. Using whole page as fallback.")
            tender = self._parse_tender_element(soup, config.get("selectors", {}))
            if tender and self.validate_tender_data(tender):
                tenders.append(tender)
            return tenders

        tender_elements = soup.select(container_selector)
        logger.info(f"Found {len(tender_elements)} tender elements using {container_selector}")

        for element in tender_elements:
            try:
                tender = self._parse_tender_element(element, config.get("selectors", {}))
                if tender and self.validate_tender_data(tender):
                    tenders.append(tender)
            except Exception as e:
                logger.error(f"Error parsing tender element: {e}")
                continue

        return tenders

    def _normalize_config(self, config: Dict) -> Dict:
        """Support both nested and legacy flat portal selector configs."""
        if not config:
            return {}

        if config.get("container_selector") and isinstance(config.get("selectors"), dict):
            return config

        selectors = {
            "title": config.get("title"),
            "reference_id": config.get("reference_id") or config.get("reference_number"),
            "agency_name": config.get("agency_name") or config.get("organization"),
            "description": config.get("description"),
            "deadline_date": config.get("deadline_date") or config.get("closing_date"),
            "published_date": config.get("published_date"),
            "detail_link": config.get("detail_link"),
        }

        return {
            "container_selector": config.get("container_selector") or config.get("list_item"),
            "selectors": selectors,
        }

    def _parse_tender_element(self, element, selectors: Dict) -> Dict:
        """Parse individual tender element"""
        def selector_css(selector_value):
            if isinstance(selector_value, str):
                return selector_value
            if isinstance(selector_value, dict):
                return selector_value.get("selector")
            return None

        def selector_text_or_attr(selector_value):
            css = selector_css(selector_value)
            if not css:
                return None

            found = element.select_one(css)
            if not found:
                return None

            if isinstance(selector_value, dict) and selector_value.get("type") == "attribute":
                attr_name = selector_value.get("attribute") or "href"
                return self.clean_text(found.get(attr_name) or "")

            return self.clean_text(found.get_text())
        
        def get_val(key):
            sel = selectors.get(key)
            if not sel:
                return None
            return selector_text_or_attr(sel)

        # Fallback logic similar to HTMLScraper
        fallback_title = self.clean_text(element.get_text()[:200])
        
        title = get_val("title") or fallback_title or f"Tender from {self.source.name}"
        ref_id = get_val("reference_id") or self.extract_reference_id(f"{self.source.id}_{title}")

        tender = {
            "title": title,
            "reference_id": ref_id,
            "description": get_val("description"),
            "agency_name": get_val("agency_name") or self.source.name,
            "deadline_date": self.normalize_date(get_val("deadline_date")),
            "published_date": self.normalize_date(get_val("published_date")),
        }

        # URL
        link_selector = selectors.get("detail_link")
        link_css = selector_css(link_selector)
        link_elem = element.select_one(link_css) if link_css else element.select_one('a')
        if link_elem and link_elem.get('href'):
            tender['source_url'] = self._make_absolute_url(link_elem['href'])
        else:
            tender['source_url'] = self.source.url

        return tender

    def _setup_driver(self):
        """Setup Selenium WebDriver with options using undetected_chromedriver"""
        options = uc.ChromeOptions()
        # Headless mode can sometimes trigger Cloudflare, but we'll try it
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        try:
            # uc.Chrome automatically handles the driver executable
            # use_subprocess=True helps avoid handle invalid errors on some Windows setups
            self.driver = uc.Chrome(options=options, use_subprocess=True)
            logger.info("Undetected WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize undetected WebDriver: {e}")
            # Fallback to standard selenium if uc fails
            try:
                from selenium.webdriver.chrome.options import Options as StdOptions
                std_options = StdOptions()
                std_options.add_argument('--headless')
                self.driver = webdriver.Chrome(options=std_options)
                logger.info("Standard WebDriver initialized as fallback")
            except Exception as e2:
                logger.error(f"Standard WebDriver fallback also failed: {e2}")
                raise

    async def _login(self) -> bool:
        """Perform login to portal"""
        try:
            username = self.source.username
            password_encrypted = self.source.encrypted_password

            if not username or not password_encrypted:
                logger.error("Missing login credentials")
                return False

            # Decrypt password
            from app.utils.encryption import decrypt_password
            password = decrypt_password(password_encrypted)

            # Navigate to login page
            login_url = self.source.login_url or (self.source.url.rsplit('/', 1)[0] + '/login')
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
        """Wait for page to fully load and handle potential challenges"""
        try:
            # First wait for document ready
            wait = WebDriverWait(self.driver, self.wait_timeout)
            wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            
            # Check if we are on a Cloudflare challenge page
            page_title = self.driver.title
            if "Cloudflare" in page_title or "Attention Required" in page_title:
                logger.info("Cloudflare challenge detected, waiting longer (30s)...")
                time.sleep(30) # Give it even more time to solve
            
            # Scroll multiple times to trigger any lazy-loaded content or anti-bot checks
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/1.5);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)

            time.sleep(5)  # General wait for dynamic content
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