import pandas as pd
import os

file_path = 'uploads/All Source Web Links.xlsx'
sheet_name = 'All_in_One_Data_Format_WA_OR'

if os.path.exists(file_path):
    # Only read first few rows to avoid memory issues with 26k rows
    df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=5)
    print(f"COLUMNS IN '{sheet_name}':")
    print(list(df.columns))
    print(f"\nSAMPLE DATA:")
    print(df.to_dict(orient='records'))
else:
    print("File not found")
