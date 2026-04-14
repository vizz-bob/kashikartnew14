import pandas as pd
xl = pd.ExcelFile('uploads/All Source Web Links.xlsx')
for s in xl.sheet_names:
    if 'Keyword' in s:
        print(f"EXACT_NAME: {repr(s)}")
        df = pd.read_excel(xl, sheet_name=s, nrows=20)
        print("COLUMNS:", df.columns.tolist())
        print(df.to_string())
