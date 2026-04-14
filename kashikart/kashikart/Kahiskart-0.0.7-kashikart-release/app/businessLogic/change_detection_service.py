from sqlalchemy.orm import Session
from typing import Dict, Optional
import hashlib
import logging

from app.models.tender import Tender

logger = logging.getLogger(__name__)


class ChangeDetectionService:

    @staticmethod
    def generate_content_hash(title: str, description: Optional[str] = None) -> str:

        content = f"{title}{description or ''}"
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def has_content_changed(tender: Tender, new_data: Dict) -> bool:


        current_hash = tender.content_hash

        new_hash = ChangeDetectionService.generate_content_hash(
            new_data.get('title', tender.title),
            new_data.get('description', tender.description)
        )

        return current_hash != new_hash

    @staticmethod
    def detect_changes(tender: Tender, new_data: Dict) -> Dict:


        changes = {}

        fields_to_check = [
            'title', 'description', 'deadline_date',
            'agency_name', 'agency_location', 'status'
        ]

        for field in fields_to_check:
            old_value = getattr(tender, field, None)
            new_value = new_data.get(field)

            if new_value is not None and old_value != new_value:
                changes[field] = {
                    'old': old_value,
                    'new': new_value
                }

        return changes

    @staticmethod
    def should_notify_change(changes: Dict) -> bool:


        # Notify for important field changes
        important_fields = ['deadline_date', 'status', 'title']

        for field in important_fields:
            if field in changes:
                return True

        return False