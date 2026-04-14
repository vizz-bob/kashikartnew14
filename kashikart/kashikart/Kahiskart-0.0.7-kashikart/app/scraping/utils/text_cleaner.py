import re
from typing import Optional


def clean_text(text: Optional[str]) -> str:
    """
    Normalize and clean scraped text safely.

    - Removes extra whitespace
    - Removes non-breaking spaces
    - Removes control characters
    - Returns empty string for None
    """

    if not text:
        return ""

    # Convert to string just in case
    text = str(text)

    # Replace HTML & control characters
    text = (
        text.replace("\xa0", " ")
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
    )

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()
