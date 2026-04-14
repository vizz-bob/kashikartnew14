import pandas as pd
import os

file_path = 'uploads/All Source Web Links.xlsx'
if os.path.exists(file_path):
    df = pd.read_excel(file_path)
    
    # Extract source name and url using the logic from the app
    sources = []
    for _, row in df.iterrows():
        data = row.to_dict()
        source_name = (
            data.get('Source') or
            data.get('source') or
            data.get('City/Agency')
        )
        source_url = (
            data.get('Web Source Data Link (Links of Tender Release Sources)') or
            data.get('Column3 (Source Link 1)') or
            data.get('Column4')
        )
        
        if source_name and source_url:
            # Handle NaN
            if pd.isna(source_name) or pd.isna(source_url):
                continue
            sources.append((str(source_name).strip(), str(source_url).strip()))
    
    unique_sources = set(sources)
    print(f"TOTAL UNIQUE SOURCES IN EXCEL: {len(unique_sources)}")
    
    # Group by name to see if there are same names with different URLs
    names = [s[0] for s in unique_sources]
    print(f"TOTAL UNIQUE SOURCE NAMES IN EXCEL: {len(set(names))}")
    
else:
    print("File not found")
