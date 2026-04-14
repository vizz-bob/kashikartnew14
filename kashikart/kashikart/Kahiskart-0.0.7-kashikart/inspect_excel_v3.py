import pandas as pd
import os

file_path = 'uploads/All Source Web Links.xlsx'
if os.path.exists(file_path):
    df = pd.read_excel(file_path)
    print("COLUMNS FOUND:")
    for i, col in enumerate(df.columns):
        print(f"{i}: {col}")
    print(f"\nTOTAL ROWS: {len(df)}")
    
    if len(df) > 0:
        first_row = df.iloc[0].to_dict()
        print("\nFIRST ROW KEYS:")
        for k in first_row.keys():
            print(f"- {k}")
        print("\nFIRST ROW VALUES (Snippets):")
        for k, v in first_row.items():
            print(f"- {k}: {str(v)[:50]}")
else:
    print(f"File not found at {file_path}")
