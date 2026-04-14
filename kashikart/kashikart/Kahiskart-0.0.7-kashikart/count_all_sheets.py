import pandas as pd
import os

file_path = 'uploads/All Source Web Links.xlsx'
if os.path.exists(file_path):
    xl = pd.ExcelFile(file_path)
    print(f"SHEETS FOUND: {xl.sheet_names}")
    
    total_unique_sources = set()
    
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"Processing sheet: {sheet_name} ({len(df)} rows)")
        
        for _, row in df.iterrows():
            data = row.to_dict()
            source_name = (
                data.get('Source') or
                data.get('source') or
                data.get('City/Agency') or
                data.get('Name')
            )
            source_url = (
                data.get('Web Source Data Link (Links of Tender Release Sources)') or
                data.get('Column3 (Source Link 1)') or
                data.get('Column4') or
                data.get('URL') or
                data.get('Link')
            )
            
            if source_name and source_url:
                if pd.isna(source_name) or pd.isna(source_url):
                    continue
                total_unique_sources.add((str(source_name).strip(), str(source_url).strip()))
                
    print(f"\nTOTAL UNIQUE SOURCES ACROSS ALL SHEETS: {len(total_unique_sources)}")
else:
    print("File not found")
