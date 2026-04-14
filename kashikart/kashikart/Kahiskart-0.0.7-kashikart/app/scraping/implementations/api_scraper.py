from typing import List, Dict
from app.scraping.base.scraper import BaseScraper
from app.scraping.utils.session_manager import SessionManager
import logging
import json
import re

logger = logging.getLogger(__name__)

class APIBasedScraper(BaseScraper):
    """
    A generic scraper for sites that expose a public JSON API.
    
    The selector_config should contain:
    {
        "api_url": "https://...",           # The API endpoint to call (GET)
        "api_method": "GET",                # GET or POST
        "api_params": {...},               # Query params (optional)
        "api_headers": {...},              # Extra headers (optional)
        "result_path": "notices",          # Dot-separated path to the list in JSON (e.g. "data.items")
        "field_mapping": {
            "title": "bid_description",
            "reference_id": "id",
            "description": "notice_type",
            "agency_name": "project_name",
            "published_date": "noticedate",
            "deadline_date": "submission_date"
        }
    }
    """

    async def scrape(self) -> List[Dict]:
        config = self.source.selector_config or {}
        api_url = config.get("api_url", self.source.url)
        api_method = config.get("api_method", "GET").upper()
        api_params = config.get("api_params", {})
        api_headers = config.get("api_headers", {})
        result_path = config.get("result_path", "")
        field_mapping = config.get("field_mapping", {})
        api_body_type = config.get("api_body_type", "json").lower()
        preflight_url = config.get("preflight_url")
        csrf_field = config.get("csrf_field")
        csrf_regex = config.get("csrf_regex")
        json_stringify_fields = set(config.get("json_stringify_fields", []))

        session = SessionManager.get_session(self.source)

        # Add extra headers
        if api_headers:
            session.headers.update(api_headers)

        # Optional preflight request for sites that need runtime CSRF tokens.
        if preflight_url and csrf_field:
            preflight_response = session.get(preflight_url, timeout=self.timeout)
            preflight_response.raise_for_status()

            page_text = preflight_response.text
            token_match = None

            if csrf_regex:
                token_match = re.search(csrf_regex, page_text)
            else:
                default_pattern = rf"{re.escape(csrf_field)}['\"]?\s*[:=]\s*['\"]([A-Za-z0-9_-]{{8,128}})['\"]"
                token_match = re.search(default_pattern, page_text)

            if not token_match:
                raise ValueError(f"Could not extract CSRF token for field '{csrf_field}'")

            csrf_token = token_match.group(1)
            api_params = self._replace_placeholder(api_params, "{{csrf_token}}", csrf_token)

        if isinstance(api_params, dict):
            for field_name in json_stringify_fields:
                if field_name in api_params:
                    api_params[field_name] = json.dumps(api_params[field_name])

        logger.info(f"Fetching API: {api_url} [{api_method}]")

        try:
            if api_method == "POST":
                if api_body_type == "form":
                    response = session.post(api_url, data=api_params, timeout=self.timeout)
                else:
                    response = session.post(api_url, json=api_params, timeout=self.timeout)
            else:
                response = session.get(api_url, params=api_params, timeout=self.timeout)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"API request failed for {self.source.name}: {e}")
            raise

        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON from {api_url}: {e}")
            raise ValueError(f"Non-JSON response from {api_url}: {e}")

        # Navigate the result_path to get the list
        items = data
        if result_path:
            for key in result_path.split("."):
                if isinstance(items, dict):
                    items = items.get(key, [])
                else:
                    items = []
                    break

        if isinstance(items, dict):
            # Some APIs return maps keyed by ID instead of a JSON array.
            # Example: {"123": {...}, "124": {...}} -> [{...}, {...}]
            items = list(items.values())
        elif not isinstance(items, list):
            logger.warning(f"Expected list/dict at path '{result_path}', got {type(items)}")
            items = []

        logger.info(f"Found {len(items)} items in API response for {self.source.name}")

        tenders = []
        for item in items:
            try:
                tender = self._map_item(item, field_mapping)
                if tender and self.validate_tender_data(tender):
                    tenders.append(tender)
            except Exception as e:
                logger.error(f"Error mapping item: {e}")

        return tenders

    def _replace_placeholder(self, value, target: str, replacement: str):
        if isinstance(value, dict):
            return {k: self._replace_placeholder(v, target, replacement) for k, v in value.items()}
        if isinstance(value, list):
            return [self._replace_placeholder(v, target, replacement) for v in value]
        if isinstance(value, str):
            return value.replace(target, replacement)
        return value

    def _map_item(self, item: Dict, field_mapping: Dict) -> Dict:
        """Map API response fields to tender fields using the field_mapping config."""
        def get_field(key):
            mapped_key = field_mapping.get(key)
            if not mapped_key:
                return None
            # Support nested keys with dot notation e.g. "project.name"
            val = item
            for part in mapped_key.split("."):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    return None

            if isinstance(val, list):
                if not val:
                    return None
                val = val[0]

            return str(val) if val is not None else None

        title = get_field("title") or f"Tender from {self.source.name}"
        ref_raw = get_field("reference_id") or title
        ref_id = self.extract_reference_id(f"{self.source.id}_{ref_raw}") if not get_field("reference_id") else get_field("reference_id")

        return {
            "title": title,
            "reference_id": ref_id,
            "description": get_field("description"),
            "agency_name": get_field("agency_name") or self.source.name,
            "published_date": self.normalize_date(get_field("published_date")),
            "deadline_date": self.normalize_date(get_field("deadline_date")),
            "source_url": self.source.url,
        }
