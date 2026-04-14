import pandas as pd
import os

file_path = 'uploads/All Source Web Links.xlsx'
sheet_name = 'Source Links FL WA OR'

if os.path.exists(file_path):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    print(f"COLUMNS IN '{sheet_name}':")
    print(list(df.columns))
    print(f"\nSAMPLE ROW (row 0):")
    print(df.iloc[0].to_dict())
    
    # Count unique sources in this sheet
    sources = []
    for _, row in df.iterrows():
        name = row.get('Source') or row.get('source')
        url = row.get('Web Source Data Link (Links of Tender Release Sources)') or row.get('Link')
        if name and url and not pd.isna(name) and not pd.isna(url):
            sources.append((str(name).strip(), str(url).strip()))
    
    print(f"\nUNIQUE SOURCES IN THIS SHEET: {len(set(sources))}")
    
else:
    print("File not found")
