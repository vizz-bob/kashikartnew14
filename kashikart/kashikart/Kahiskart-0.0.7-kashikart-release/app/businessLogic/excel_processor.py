import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.onedrive import (
    ExcelFileTracker, RawExcelSheet, FileStatus, SheetHeaderMapping
)
from app.businessLogic.onedrive_service import OneDriveService

logger = logging.getLogger(__name__)

class ExcelProcessor:
    """Process Excel files and store data in database"""
    
    def __init__(self, db: Session):
        self.db = db
        self.onedrive_service = OneDriveService()
    
    def process_onedrive_file(self, share_link: str, force_refresh: bool = False) -> Optional[ExcelFileTracker]:
        """
        Main method to download and process OneDrive Excel file
        
        Args:
            share_link: OneDrive share link
            force_refresh: Force reprocessing even if file hasn't changed
            
        Returns:
            ExcelFileTracker object or None
        """
        try:
            # Download file
            logger.info(f"Downloading Excel file from OneDrive...")
            file_content = self.onedrive_service.download_excel_file(share_link)
            
            if not file_content:
                logger.error("Failed to download Excel file")
                return None
            
            # Calculate hash
            file_hash = self.onedrive_service.calculate_file_hash(file_content)
            logger.info(f"File hash: {file_hash}")
            
            # Check if file already processed
            if not force_refresh:
                existing_file = self.db.query(ExcelFileTracker).filter(
                    ExcelFileTracker.file_hash == file_hash
                ).first()
                
                if existing_file and existing_file.status == FileStatus.DONE:
                    logger.info(f"File already processed (file_id: {existing_file.file_id})")
                    return existing_file
            
            # Read all sheets
            sheets_data = self.onedrive_service.read_excel_sheets(file_content)
            
            if not sheets_data:
                logger.error("No sheets found in Excel file")
                return None
            
            # Create file tracker record
            file_tracker = ExcelFileTracker(
                file_name="OneDrive_Tenders_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
                sheet_count=len(sheets_data),
                status=FileStatus.PROCESSING,
                file_hash=file_hash,
                onedrive_file_id=share_link,
                last_modified=datetime.utcnow()
            )
            
            self.db.add(file_tracker)
            self.db.commit()
            self.db.refresh(file_tracker)
            
            logger.info(f"Created file tracker record (file_id: {file_tracker.file_id})")
            
            # Process each sheet
            total_rows = 0
            for sheet_name, df in sheets_data.items():
                try:
                    rows_processed = self._process_sheet(
                        file_tracker.file_id,
                        sheet_name,
                        df
                    )
                    total_rows += rows_processed
                    logger.info(f"Processed {rows_processed} rows from sheet '{sheet_name}'")
                except Exception as e:
                    logger.error(f"Error processing sheet '{sheet_name}': {str(e)}", exc_info=True)
                    continue
            
            # Update file tracker
            file_tracker.status = FileStatus.DONE
            file_tracker.processed_at = datetime.utcnow()
            file_tracker.total_rows = total_rows
            self.db.commit()
            
            logger.info(f"Successfully processed {total_rows} total rows from {len(sheets_data)} sheets")
            return file_tracker
            
        except Exception as e:
            logger.error(f"Error processing OneDrive file: {str(e)}", exc_info=True)
            if 'file_tracker' in locals():
                file_tracker.status = FileStatus.FAILED
                file_tracker.error_message = str(e)
                self.db.commit()
            return None
    
    def _process_sheet(self, file_id: int, sheet_name: str, df: pd.DataFrame) -> int:
        """
        Process individual sheet and store rows
        
        Args:
            file_id: File tracker ID
            sheet_name: Name of the sheet
            df: DataFrame containing sheet data
            
        Returns:
            Number of rows processed
        """
        if df.empty:
            logger.warning(f"Sheet '{sheet_name}' is empty")
            return 0
        
        # Get or create header mapping
        header_mapping = self._get_or_create_header_mapping(sheet_name, df)
        
        # Extract source website from sheet name if possible
        source_website = self._extract_source_from_sheet_name(sheet_name)
        
        # Process rows in batches
        batch_size = 1000
        rows_processed = 0
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_records = []
            
            for idx, row in batch_df.iterrows():
                try:
                    # Convert row to JSON, handling NaN and datetime
                    row_dict = self._row_to_json(row, header_mapping)
                    
                    # Extract tender_id if available
                    tender_id = self._extract_tender_id(row_dict)
                    
                    raw_sheet = RawExcelSheet(
                        file_id=file_id,
                        sheet_name=sheet_name,
                        row_number=idx + 1,
                        row_json=row_dict,
                        source_website=source_website,
                        tender_id=tender_id
                    )
                    
                    batch_records.append(raw_sheet)
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx} in sheet '{sheet_name}': {str(e)}")
                    continue
            
            # Bulk insert batch
            if batch_records:
                self.db.bulk_save_objects(batch_records)
                self.db.commit()
                rows_processed += len(batch_records)
        
        return rows_processed
    
    def _get_or_create_header_mapping(self, sheet_name: str, df: pd.DataFrame) -> Dict[str, str]:
        """Get existing header mapping or create new one"""
        mapping = self.db.query(SheetHeaderMapping).filter(
            SheetHeaderMapping.sheet_name == sheet_name
        ).first()
        
        if mapping:
            return mapping.header_mapping
        
        # Detect common tender fields
        detected_mapping = self.onedrive_service.detect_tender_fields(df)
        
        # Create new mapping
        new_mapping = SheetHeaderMapping(
            sheet_name=sheet_name,
            source_website=self._extract_source_from_sheet_name(sheet_name),
            header_mapping=detected_mapping
        )
        
        self.db.add(new_mapping)
        self.db.commit()
        
        return detected_mapping
    
    def _row_to_json(self, row: pd.Series, header_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Convert pandas row to JSON with proper type handling"""
        row_dict = {}
        
        for col, value in row.items():
            # Handle NaN values
            if pd.isna(value):
                row_dict[col] = None
            # Handle datetime
            elif isinstance(value, (pd.Timestamp, datetime)):
                row_dict[col] = value.isoformat()
            # Handle numeric types
            elif isinstance(value, (int, float)):
                row_dict[col] = float(value) if isinstance(value, float) else int(value)
            # Everything else as string
            else:
                row_dict[col] = str(value)
        
        # Add normalized fields if mapping exists
        if header_mapping:
            normalized_fields = {}
            for field, original_col in header_mapping.items():
                if original_col in row_dict:
                    normalized_fields[f"normalized_{field}"] = row_dict[original_col]
            row_dict.update(normalized_fields)
        
        return row_dict
    
    def _extract_source_from_sheet_name(self, sheet_name: str) -> Optional[str]:
        """Extract source website from sheet name"""
        # Common patterns in sheet names
        sheet_lower = sheet_name.lower()
        
        source_patterns = {
            'gem': 'GeM Portal',
            'eprocure': 'eProcurement',
            'cppp': 'CPPP Portal',
            'etender': 'eTender',
            'ireps': 'IREPS',
            'sam': 'SAM.gov',
            'ted': 'TED Europa',
        }
        
        for pattern, source in source_patterns.items():
            if pattern in sheet_lower:
                return source
        
        return sheet_name
    
    def _extract_tender_id(self, row_dict: Dict[str, Any]) -> Optional[str]:
        """Extract tender ID from row data"""
        # Check normalized field first
        if 'normalized_tender_id' in row_dict and row_dict['normalized_tender_id']:
            return str(row_dict['normalized_tender_id'])
        
        # Check common field names
        possible_fields = ['tender_id', 'tender_no', 'reference_no', 'ref_no', 'id']
        for field in possible_fields:
            for key, value in row_dict.items():
                if field in key.lower() and value:
                    return str(value)
        
        return None
    
    def get_latest_file_info(self) -> Optional[ExcelFileTracker]:
        """Get information about the latest processed file"""
        return self.db.query(ExcelFileTracker).order_by(
            ExcelFileTracker.uploaded_at.desc()
        ).first()
    
    def get_sheet_data(
        self, 
        file_id: Optional[int] = None,
        sheet_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[RawExcelSheet]:
        """Get sheet data with optional filtering"""
        query = self.db.query(RawExcelSheet)
        
        if file_id:
            query = query.filter(RawExcelSheet.file_id == file_id)
        
        if sheet_name:
            query = query.filter(RawExcelSheet.sheet_name == sheet_name)
        
        return query.offset(offset).limit(limit).all()