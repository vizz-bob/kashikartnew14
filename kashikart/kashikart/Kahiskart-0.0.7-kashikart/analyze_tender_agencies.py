import pandas as pd
import os

file_path = 'uploads/All Source Web Links.xlsx'
sheet_name = 'All_in_One_Data_Format_WA_OR'

if os.path.exists(file_path):
    df = pd.read_excel(file_path, sheet_name=sheet_name, usecols=['City/Agency'])
    unique_agencies = df['City/Agency'].dropna().unique()
    print(f"TOTAL UNIQUE AGENCIES IN TENDER SHEET: {len(unique_agencies)}")
    print(f"TOTAL ROWS IN TENDER SHEET: {len(df)}")
else:
    print("File not found")
