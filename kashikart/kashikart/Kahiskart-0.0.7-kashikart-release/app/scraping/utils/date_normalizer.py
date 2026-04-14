from datetime import datetime, date
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:


    if not text:
        return ""

    # Remove extra whitespace
    text = ' '.join(text.split())

    # Remove special characters
    text = text.replace('\\xa0', ' ')
    text = text.replace('\\n', ' ')
    text = text.replace('\\r', ' ')
    text = text.replace('\\t', ' ')

    return text.strip()


def parse_date(date_str: str) -> Optional[date]:


    if not date_str:
        return None

    # Clean the string
    date_str = clean_text(date_str)

    # Try common date formats
    formats = [
        '%m/%d/%Y',  # 01/15/2024
        '%m-%d-%Y',  # 01-15-2024
        '%d/%m/%Y',  # 15/01/2024
        '%Y-%m-%d',  # 2024-01-15
        '%b %d, %Y',  # Jan 15, 2024
        '%B %d, %Y',  # January 15, 2024
        '%d %b %Y',  # 15 Jan 2024
        '%d %B %Y',  # 15 January 2024
        '%m/%d/%y',  # 01/15/24
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None


def extract_phone(text: str) -> Optional[str]:


    pattern = r'\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b'
    match = re.search(pattern, text)

    return match.group(0) if match else None


def extract_email(text: str) -> Optional[str]:


    pattern = r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
    match = re.search(pattern, text)

    return match.group(0) if match else None


def extract_dollar_amount(text: str) -> Optional[float]:


    pattern = r'\\$([\\d,]+(?:\\.\\d{2})?)'
    match = re.search(pattern, text)

    if match:
        amount_str = match.group(1).replace(',', '')
        try:
            return float(amount_str)
        except ValueError:
            pass

    return None