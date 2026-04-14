import pandas as pd
import os

file_path = 'uploads/All Source Web Links.xlsx'
if os.path.exists(file_path):
    xl = pd.ExcelFile(file_path)
    print("SHEETS AND ROW COUNTS:")
    for name in xl.sheet_names:
        df = pd.read_excel(file_path, sheet_name=name)
        print(f"- {name}: {len(df)} rows")
else:
    print("File not found")
