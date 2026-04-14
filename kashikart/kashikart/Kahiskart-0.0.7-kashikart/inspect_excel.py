import pandas as pd
import sys

file_path = r'C:\Users\katas\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\BE1CA8A7B43BD93E2F5923CF7764A13B18F621E4\transfers\2026-11\All Source Web Links (1).xlsx'

try:
    df = pd.read_excel(file_path)
    with open('excel_inspection_report.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total rows: {len(df)}\n")
        f.write(f"Columns: {df.columns.tolist()}\n")
        f.write("\nSample Data (First 20 rows):\n")
        f.write(df.head(20).to_string())
    print("Report written to excel_inspection_report.txt")
except Exception as e:
    print(f"Error: {e}")
