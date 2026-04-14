# import pandas as pd
# import hashlib
# import json
# import math
# from datetime import datetime
# from sqlalchemy import insert
# from app.core.sync_database import SyncSessionLocal, engine_sync
# from app.models.excel_raw import ExcelFile, ExcelSheet, ExcelRowRaw


# CHUNK_SIZE = 1000


# class ExcelProcessorSync:

#     # ================= CLEAN JSON =================
#     @staticmethod
#     def clean_json_row(row_dict):
#         clean = {}
#         for k, v in row_dict.items():
#             if pd.isna(v):
#                 clean[k] = None
#             else:
#                 clean[k] = str(v).strip()
#         return clean

#     # ================= HASH =================
#     @staticmethod
#     def row_hash(file_path, sheet_name, row_index, row_dict):
#         base = f"{file_path}|{sheet_name}|{row_index}|{json.dumps(row_dict, sort_keys=True)}"
#         return hashlib.sha256(base.encode()).hexdigest()

#     # ================= MAIN =================
#     @staticmethod
#     def process_all_registered_files():
#         print("\nAUTO EXCEL FETCH START")

#         db = SyncSessionLocal()
#         files = db.query(ExcelFile).all()
#         db.close()

#         print(f"TOTAL FILES: {len(files)}")

#         for file in files:
#             ExcelProcessorSync.process_file(file.id, file.file_path)

#         print("\nAUTO EXCEL FETCH DONE")

#     # ================= PROCESS FILE =================
#     @staticmethod
#     def process_file(file_id, file_path):
#         file_path = file_path.replace("\\", "/")
#         print(f"\nProcessing File: {file_path}")

#         excel = pd.ExcelFile(file_path)
#         for sheet_name in excel.sheet_names:
#             ExcelProcessorSync.process_sheet(file_id, file_path, sheet_name)

#     # ================= PROCESS SHEET =================
#     @staticmethod
#     def process_sheet(file_id, file_path, sheet_name):
#         print(f"  Sheet: {sheet_name}")

#         df = pd.read_excel(file_path, sheet_name=sheet_name)
#         print(f"  Rows: {len(df)}")

#         db = SyncSessionLocal()

#         # get/create sheet
#         sheet = db.query(ExcelSheet).filter_by(
#             excel_file_id=file_id,
#             sheet_name=sheet_name
#         ).first()

#         if not sheet:
#             sheet = ExcelSheet(excel_file_id=file_id, sheet_name=sheet_name)
#             db.add(sheet)
#             db.commit()
#             db.refresh(sheet)

#         db.close()

#         # chunk insert
#         for start in range(0, len(df), CHUNK_SIZE):
#             chunk = df.iloc[start:start+CHUNK_SIZE]
#             ExcelProcessorSync.insert_chunk(sheet.id, file_path, sheet_name, chunk)

#     # ================= FAST INSERT IGNORE =================
#     @staticmethod
#     def insert_chunk(sheet_id, file_path, sheet_name, df_chunk):
#         records = []

#         for idx, row in df_chunk.iterrows():
#             row_dict = ExcelProcessorSync.clean_json_row(row.to_dict())

#             # skip empty rows
#             if all(v is None for v in row_dict.values()):
#                 continue

#             hash_value = ExcelProcessorSync.row_hash(file_path, sheet_name, idx, row_dict)

#             records.append({
#                 "sheet_id": sheet_id,
#                 "row_index": int(idx),
#                 "row_data": row_dict,
#                 "row_hash": hash_value,
#                 "created_at": datetime.utcnow()
#             })

#         if not records:
#             print("    Skipped empty chunk")
#             return

#         # MYSQL INSERT IGNORE
#         stmt = insert(ExcelRowRaw).prefix_with("IGNORE")

#         with engine_sync.begin() as conn:
#             conn.execute(stmt, records)

#         print(f"    Inserted Chunk: {len(records)} rows")

import pandas as pd
import hashlib
import json
from datetime import datetime
from sqlalchemy import insert, text
from app.core.sync_database import SyncSessionLocal, engine_sync
from app.models.excel_raw import ExcelFile, ExcelSheet, ExcelRowRaw
from app.models.excel_ingestion_meta import ExcelIngestionMeta


CHUNK_SIZE = 2000


class ExcelProcessorSync:

    # ================= FILE HASH =================
    @staticmethod
    def file_hash(path):
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        return sha.hexdigest()

    # ================= CLEAN JSON =================
    @staticmethod
    def clean_json_row(row_dict):
        return {k: None if pd.isna(v) else str(v).strip() for k, v in row_dict.items()}

    # ================= ROW HASH =================
    @staticmethod
    def row_hash(file_path, sheet_name, row_index, row_dict):
        base = f"{file_path}|{sheet_name}|{row_index}|{json.dumps(row_dict, sort_keys=True)}"
        return hashlib.sha256(base.encode()).hexdigest()

    # ================= MAIN =================
    @staticmethod
    def process_all_registered_files():

        print("\n [ AUTO EXCEL FETCH START ]")


        db = SyncSessionLocal()
        files = db.query(ExcelFile).all()
        db.close()

        print(f"TOTAL FILES: {len(files)}")

        for file in files:
            ExcelProcessorSync.process_file(file.id, file.file_path)

        print("\n • AUTO EXCEL FETCH DONE •")

    # ================= PROCESS FILE =================
    @staticmethod
    def process_file(file_id, file_path):
        file_path = file_path.replace("\\", "/")
        print(f"\n[</>] Processing File: {file_path}")

        # ---------- CHANGE DETECTION ----------
        current_hash = ExcelProcessorSync.file_hash(file_path)

        db = SyncSessionLocal()

        old_hash = db.query(ExcelIngestionMeta.file_hash)\
            .filter(ExcelIngestionMeta.file_path == file_path)\
            .order_by(ExcelIngestionMeta.id.desc())\
            .first()

        if old_hash and old_hash[0] == current_hash:
            print("[!] No changes detected. Skipping ingestion.")
            db.close()
            return

        print("⁘ Change detected. Starting ingestion...")
        db.close()

        excel = pd.ExcelFile(file_path)
        for sheet_name in excel.sheet_names:
            ExcelProcessorSync.process_sheet(file_id, file_path, sheet_name)

        # Save new hash
        db = SyncSessionLocal()
        db.add(ExcelIngestionMeta(file_path=file_path, file_hash=current_hash))
        db.commit()
        db.close()

        print("✓ FILE INGESTION COMPLETE")

    # ================= PROCESS SHEET =================
    @staticmethod
    def process_sheet(file_id, file_path, sheet_name):
        print(f"  <../../..> Sheet: {sheet_name}")

        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"  Rows: {len(df)}")

        db = SyncSessionLocal()

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

        # CHUNK PROCESS
        for start in range(0, len(df), CHUNK_SIZE):
            chunk = df.iloc[start:start+CHUNK_SIZE]
            ExcelProcessorSync.insert_chunk(sheet.id, file_path, sheet_name, chunk)

    # ================= ULTRA FAST INSERT =================
    @staticmethod
    def insert_chunk(sheet_id, file_path, sheet_name, df_chunk):
        records = []

        for idx, row in df_chunk.iterrows():
            row_dict = ExcelProcessorSync.clean_json_row(row.to_dict())

            if all(v is None for v in row_dict.values()):
                continue

            hash_value = ExcelProcessorSync.row_hash(file_path, sheet_name, idx, row_dict)

            records.append({
                "sheet_id": sheet_id,
                "row_index": int(idx),
                "row_data": row_dict,
                "row_hash": hash_value,
                "created_at": datetime.utcnow()
            })

        if not records:
            print("    ¡!¡ Skipped empty chunk")
            return

        stmt = insert(ExcelRowRaw).prefix_with("IGNORE")

        with engine_sync.begin() as conn:
            conn.execute(stmt, records)

        print(f"    ✓ Inserted Chunk: {len(records)} rows")
