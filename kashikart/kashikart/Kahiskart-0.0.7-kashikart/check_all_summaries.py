import pandas as pd
xl = pd.ExcelFile('uploads/All Source Web Links.xlsx')
for sn in xl.sheet_names:
    if 'Summary' in sn or 'Source' in sn:
        print(f"\n--- SHEET: {sn} ---")
        df = pd.read_excel(xl, sheet_name=sn, nrows=5)
        print(f"Columns: {list(df.columns)}")
        print(f"Sample Row 0: {df.iloc[0].to_dict() if len(df) > 0 else 'Empty'}")
