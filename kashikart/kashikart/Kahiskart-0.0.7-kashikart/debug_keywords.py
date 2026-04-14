import pandas as pd
xl = pd.ExcelFile('uploads/All Source Web Links.xlsx')
keywords_sheets = [s for s in xl.sheet_names if 'Keyword' in s]
print(f"FOUND KEYWORD SHEETS: {keywords_sheets}")
for s in keywords_sheets:
    df = pd.read_excel(xl, sheet_name=s, nrows=5)
    print(f"\n--- {s} ---")
    print(list(df.columns))
    print(df.head(3).to_string())
