import pandas as pd
xl = pd.ExcelFile('uploads/All Source Web Links.xlsx')
for sn in xl.sheet_names:
    print(f"\nSHEET: {sn}")
    try:
        df = pd.read_excel(xl, sheet_name=sn, nrows=3)
        print(f"Columns: {list(df.columns)}")
        print(f"Row 0: {df.iloc[0].to_dict() if len(df) > 0 else 'Empty'}")
    except Exception as e:
        print(f"Error: {e}")
