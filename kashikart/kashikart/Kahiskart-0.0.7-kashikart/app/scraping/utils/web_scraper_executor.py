import json
from typing import List, Dict, Any
from bs4 import BeautifulSoup

class WebScraperExecutor:
    """
    Executes a Web Scraper.io sitemap using BeautifulSoup for static parsing.
    Extensible to Playwright for dynamic parsing.
    """
    
    def __init__(self, sitemap_json: str):
        self.sitemap = json.loads(sitemap_json)
        self.selectors = {s['id']: s for s in self.sitemap.get('selectors', [])}
        
    def execute(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Start from _root selectors
        root_selectors = [s for s in self.selectors.values() if '_root' in s.get('parentSelectors', [])]
        
        # Find the main container selector (usually multiple: true)
        main_selector = next((s for s in root_selectors if s.get('multiple')), None)
        
        if not main_selector:
            # If no multiple selector at root, try to extract a single object
            return [self._extract_fields(soup, '_root')]

        containers = soup.select(main_selector['selector'])
        for container in containers:
            item = self._extract_fields(container, main_selector['id'])
            if item:
                results.append(item)
                
        return results

    def _extract_fields(self, element, parent_id: str) -> Dict[str, Any]:
        data = {}
        child_selectors = [s for s in self.selectors.values() if parent_id in s.get('parentSelectors', [])]
        
        for selector in child_selectors:
            if selector['type'] == 'SelectorText':
                found = element.select_one(selector['selector'])
                data[selector['id']] = found.get_text(strip=True) if found else None
            elif selector['type'] == 'SelectorLink':
                found = element.select_one(selector['selector'])
                data[selector['id']] = found.get('href') if found else None
            elif selector['type'] == 'SelectorImage':
                found = element.select_one(selector['selector'])
                data[selector['id']] = found.get('src') if found else None
            # Recursive elements would go here
            
        return data
