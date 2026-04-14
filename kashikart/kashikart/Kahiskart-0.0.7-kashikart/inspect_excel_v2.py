import pandas as pd
import os

file_path = 'uploads/All Source Web Links.xlsx'
if os.path.exists(file_path):
    df = pd.read_excel(file_path)
    print("COLUMNS FOUND:")
    for i, col in enumerate(df.columns):
        print(f"{i}: [{col}]")
    print(f"\nTOTAL ROWS: {len(df)}")
    print("\nSAMPLE DATA (First 2 rows):")
    print(df.head(2).to_dict(orient='records'))
else:
    print(f"File not found at {file_path}")
