from typing import List, Dict, Optional
import requests
import PyPDF2
import re
import logging
from io import BytesIO
from datetime import datetime

from app.scraping.base.scraper import BaseScraper
from app.models.source import Source

logger = logging.getLogger(__name__)


class PDFScraper(BaseScraper):


    def scrape(self) -> List[Dict]:


        try:
            # Download PDF
            response = requests.get(
                self.source.url,
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent}
            )
            response.raise_for_status()

            # Parse PDF
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Extract text from all pages
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()

            # Parse tenders from text
            tenders = self.parse_pdf_text(text)

            logger.info(f"Extracted {len(tenders)} tenders from PDF: {self.source.name}")

            return tenders

        except Exception as e:
            logger.error(f"Error scraping PDF from {self.source.name}: {str(e)}")
            raise

    def parse_pdf_text(self, text: str) -> List[Dict]:


        tenders = []

        # Split into sections (common patterns)
        sections = self.split_into_sections(text)

        for section in sections:
            tender = self.extract_tender_from_section(section)
            if tender and self.validate_tender_data(tender):
                tenders.append(tender)

        return tenders

    def split_into_sections(self, text: str) -> List[str]:


        # Try common delimiters
        patterns = [
            r'\n\d+\.\s+',  # 1. Title
            r'\nSolicitation\s+\w+',  # Solicitation ABC123
            r'\nRFP\s+\w+',  # RFP ABC123
            r'\n={3,}',  # ===
            r'\n-{3,}'  # ---
        ]

        for pattern in patterns:
            sections = re.split(pattern, text)
            if len(sections) > 1:
                return [s.strip() for s in sections if s.strip()]

        # If no clear delimiter, treat entire text as one tender
        return [text]

    def extract_tender_from_section(self, section: str) -> Optional[Dict]:


        # Extract title (usually first line)
        lines = section.split('\\n')
        title = self.clean_text(lines[0]) if lines else None

        if not title or len(title) < 10:
            return None

        # Extract reference ID
        ref_match = re.search(r'(RFP|IFB|RFQ|Solicitation)[-\s#:]*([A-Z0-9-]+)', section, re.IGNORECASE)
        reference_id = ref_match.group(0) if ref_match else self.extract_reference_id(title)

        # Extract agency
        agency_match = re.search(r'Agency:?\s*([^\\n]+)', section, re.IGNORECASE)
        agency_name = self.clean_text(agency_match.group(1)) if agency_match else None

        # Extract dates
        published_date = None
        deadline_date = None

        # Published date patterns
        pub_patterns = [
            r'Posted:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Published:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]

        for pattern in pub_patterns:
            match = re.search(pattern, section, re.IGNORECASE)
            if match:
                published_date = self.normalize_date(match.group(1))
                break

        # Deadline date patterns
        dead_patterns = [
            r'Due:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Deadline:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Response.*?:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]

        for pattern in dead_patterns:
            match = re.search(pattern, section, re.IGNORECASE)
            if match:
                deadline_date = self.normalize_date(match.group(1))
                break

        # Extract description (everything after title)
        description = self.clean_text('\\n'.join(lines[1:5])) if len(lines) > 1 else None

        tender = {
            'title': title,
            'reference_id': reference_id,
            'description': description,
            'agency_name': agency_name,
            'agency_location': None,
            'published_date': published_date,
            'deadline_date': deadline_date,
            'source_url': self.source.url,
            'attachments': [{
                'name': 'PDF Document',
                'url': self.source.url,
                'type': 'pdf'
            }]
        }

        return tender