import pandas as pd
xl = pd.ExcelFile('uploads/All Source Web Links.xlsx')
s = [s for s in xl.sheet_names if 'Keyword' in s][0]
df = pd.read_excel(xl, sheet_name=s, nrows=5)
for i, row in df.iterrows():
    print(f"ROW {i}")
    for j, val in enumerate(row):
        print(f"  [{j}] {df.columns[j]}: {val}")
