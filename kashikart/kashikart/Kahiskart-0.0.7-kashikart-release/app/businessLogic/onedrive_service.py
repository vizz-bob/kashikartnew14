import requests
import hashlib
import logging
from io import BytesIO
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd
from urllib.parse import quote, urlparse, parse_qs

logger = logging.getLogger(__name__)

class OneDriveService:
    """Service to download and process Excel files from OneDrive share links"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def convert_share_link_to_download_url(self, share_link: str) -> str:
        """
        Convert OneDrive share link to direct download URL
        
        Example:
        Input: https://1drv.ms/x/c/f67fbf1404d040f0/IQBEdJOqUtwbQKqYy7MGZd9WAajrSyGplGbPEZw_xWNrpI0?e=SSvtEX
        Output: Direct download URL
        """
        try:
            # Method 1: Direct conversion for Excel files
            if '1drv.ms' in share_link:
                # Extract the resource ID
                parts = share_link.split('/')
                if len(parts) >= 5:
                    resource_id = parts[-1].split('?')[0]
                    base_id = parts[4]
                    
                    # Construct direct download URL
                    download_url = f"https://api.onedrive.com/v1.0/shares/u!{self._encode_share_url(share_link)}/root/content"
                    return download_url
            
            # Method 2: Use embed URL conversion
            if 'onedrive.live.com' in share_link or '1drv.ms' in share_link:
                # Convert to embed URL first, then to download
                encoded_url = quote(share_link, safe='')
                download_url = f"https://api.onedrive.com/v1.0/shares/u!{encoded_url}/root/content"
                return download_url
            
            return share_link
            
        except Exception as e:
            logger.error(f"Error converting share link: {str(e)}")
            return share_link
    
    def _encode_share_url(self, url: str) -> str:
        """Encode share URL for OneDrive API"""
        # Base64 encode the URL
        import base64
        encoded = base64.b64encode(url.encode()).decode()
        # Make it URL safe
        encoded = encoded.rstrip('=').replace('/', '_').replace('+', '-')
        return encoded
    
    def download_excel_file(self, share_link: str) -> Optional[BytesIO]:
        """
        Download Excel file from OneDrive share link
        
        Args:
            share_link: OneDrive share link
            
        Returns:
            BytesIO object containing the Excel file or None
        """
        try:
            # Try direct download first
            download_url = self.convert_share_link_to_download_url(share_link)
            
            logger.info(f"Attempting to download from: {download_url}")
            response = self.session.get(download_url, timeout=60, allow_redirects=True)
            
            # If direct download fails, try alternate method
            if response.status_code != 200:
                logger.warning(f"Direct download failed with status {response.status_code}, trying alternate method")
                download_url = self._get_alternate_download_url(share_link)
                response = self.session.get(download_url, timeout=60, allow_redirects=True)
            
            if response.status_code == 200:
                logger.info(f"Successfully downloaded file, size: {len(response.content)} bytes")
                return BytesIO(response.content)
            else:
                logger.error(f"Failed to download file. Status: {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading Excel file: {str(e)}", exc_info=True)
            return None
    
    def _get_alternate_download_url(self, share_link: str) -> str:
        """Get alternate download URL by adding download parameter"""
        if '?' in share_link:
            return f"{share_link}&download=1"
        else:
            return f"{share_link}?download=1"
    
    def calculate_file_hash(self, file_content: BytesIO) -> str:
        """Calculate MD5 hash of file content for change detection"""
        file_content.seek(0)
        file_hash = hashlib.md5(file_content.read()).hexdigest()
        file_content.seek(0)
        return file_hash
    
    def read_excel_sheets(self, file_content: BytesIO) -> Dict[str, pd.DataFrame]:
        """
        Read all sheets from Excel file
        
        Args:
            file_content: BytesIO object containing Excel file
            
        Returns:
            Dictionary with sheet names as keys and DataFrames as values
        """
        try:
            file_content.seek(0)
            excel_file = pd.ExcelFile(file_content, engine='openpyxl')
            
            sheets_data = {}
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    sheets_data[sheet_name] = df
                    logger.info(f"Read sheet '{sheet_name}' with {len(df)} rows and {len(df.columns)} columns")
                except Exception as e:
                    logger.error(f"Error reading sheet '{sheet_name}': {str(e)}")
                    continue
            
            return sheets_data
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}", exc_info=True)
            return {}
    
    def get_file_metadata(self, share_link: str) -> Optional[Dict[str, Any]]:
        """Get metadata about the OneDrive file (requires API access)"""
        # This would require Microsoft Graph API authentication
        # For now, return basic metadata from download
        return {
            'share_link': share_link,
            'last_checked': datetime.utcnow().isoformat()
        }
    
    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to handle different header formats"""
        # Remove extra spaces, convert to lowercase, replace special chars
        df.columns = [
            str(col).strip().lower()
            .replace(' ', '_')
            .replace('-', '_')
            .replace('/', '_')
            .replace('(', '')
            .replace(')', '')
            for col in df.columns
        ]
        return df
    
    def detect_tender_fields(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Detect common tender fields across different sheet formats
        
        Returns mapping of normalized field name to original column name
        """
        common_patterns = {
            'tender_id': ['tender_no', 'tender_id', 'reference_no', 'ref_no', 'id'],
            'title': ['title', 'tender_title', 'description', 'subject'],
            'organization': ['organization', 'dept', 'department', 'buyer', 'agency'],
            'deadline': ['deadline', 'due_date', 'closing_date', 'submission_date'],
            'publish_date': ['publish_date', 'posted_date', 'publication_date'],
            'value': ['value', 'estimated_value', 'contract_value', 'amount'],
            'status': ['status', 'tender_status'],
            'category': ['category', 'type', 'tender_type'],
            'location': ['location', 'place', 'city', 'state']
        }
        
        column_mapping = {}
        df_columns_lower = [col.lower() for col in df.columns]
        
        for field, patterns in common_patterns.items():
            for pattern in patterns:
                matching_cols = [col for col in df_columns_lower if pattern in col]
                if matching_cols:
                    # Use the first match
                    original_col = df.columns[df_columns_lower.index(matching_cols[0])]
                    column_mapping[field] = original_col
                    break
        
        return column_mapping