import pandas as pd
import os

file_path = r"uploads/All Source Web Links.xlsx"
if os.path.exists(file_path):
    xls = pd.ExcelFile(file_path)
    for sheet in xls.sheet_names:
        print(f"\nSheet: {sheet}")
        df = pd.read_excel(file_path, sheet_name=sheet, nrows=1)
        for i, col in enumerate(df.columns):
            print(f"  {i}: {col}")
        print("-" * 20)
else:
    print(f"File not found: {file_path}")
