import pandas as pd
import hashlib
import json
import math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import insert
from app.core.sync_database import SyncSessionLocal, engine
from app.models.excel_raw import ExcelFile, ExcelSheet, ExcelRowRaw


MAX_WORKERS = 4       # threads
CHUNK_SIZE = 2000     # rows per batch


class ExcelProcessorParallel:

    # =========================
    # CLEAN JSON
    # =========================
    @staticmethod
    def clean_json_row(row_dict):
        for k, v in row_dict.items():
            if isinstance(v, float) and math.isnan(v):
                row_dict[k] = None
        return row_dict

    # =========================
    # HASH
    # =========================
    @staticmethod
    def row_hash(row_dict):
        clean = {k: "" if v is None else str(v).strip() for k, v in row_dict.items()}
        return hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()

    # =========================
    # MAIN ENTRY
    # =========================
    @staticmethod
    def process_all_registered_files():
        print("\n🔥 PARALLEL AUTO EXCEL FETCH START")

        db = SyncSessionLocal()
        files = db.query(ExcelFile).all()
        db.close()

        print(f"TOTAL FILES: {len(files)}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for file in files:
                executor.submit(ExcelProcessorParallel.process_file, file.id, file.file_path)

        print("\n🔥 PARALLEL AUTO EXCEL FETCH DONE")

    # =========================
    # PROCESS SINGLE FILE
    # =========================
    @staticmethod
    def process_file(file_id, file_path):
        file_path = file_path.replace("\\", "/")
        print(f"\nProcessing File: {file_path}")

        excel = pd.ExcelFile(file_path)
        for sheet_name in excel.sheet_names:
            ExcelProcessorParallel.process_sheet(file_id, file_path, sheet_name)

    # =========================
    # PROCESS SHEET (CHUNKED)
    # =========================
    @staticmethod
    def process_sheet(file_id, file_path, sheet_name):
        print(f"  Sheet: {sheet_name}")

        db = SyncSessionLocal()

        # get/create sheet
        sheet = db.query(ExcelSheet).filter_by(
            excel_file_id=file_id,
            sheet_name=sheet_name
        ).first()

        if not sheet:
            sheet = ExcelSheet(excel_file_id=file_id, sheet_name=sheet_name)
            db.add(sheet)
            db.commit()
            db.refresh(sheet)

        db.close()

        # Read Excel in chunks
        for chunk in pd.read_excel(file_path, sheet_name=sheet_name, chunksize=CHUNK_SIZE):
            ExcelProcessorParallel.insert_chunk(sheet.id, chunk)

    # =========================
    # FAST BULK INSERT IGNORE DUPLICATES
    # =========================
    @staticmethod
    def insert_chunk(sheet_id, df_chunk):
        records = []

        for idx, row in df_chunk.iterrows():
            row_dict = row.to_dict()
            # Skip row if all values are NaN
            if all(pd.isna(v) for v in row_dict.values()):
                continue

            # Clean JSON (NaN -> None)
            row_dict = ExcelProcessorParallel.clean_json_row(row_dict)

            # Generate hash
            hash_value = ExcelProcessorParallel.row_hash(row_dict)

            records.append({
                "sheet_id": sheet_id,
                "row_index": int(idx) if not pd.isna(idx) else None,
                "row_data": row_dict,
                "row_hash": hash_value,
                "created_at": datetime.utcnow()
            })

        if not records:
            print(f"    Skipped chunk: empty or duplicate rows")
            return

        # INSERT IGNORE DUPLICATES (MYSQL SAFE)
        stmt = insert(ExcelRowRaw).prefix_with("IGNORE")
        with engine.begin() as conn:
            conn.execute(stmt, records)

        print(f"    Inserted Chunk: {len(records)} rows")
