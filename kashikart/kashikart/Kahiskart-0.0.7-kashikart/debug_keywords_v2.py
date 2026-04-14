import pandas as pd
xl = pd.ExcelFile('uploads/All Source Web Links.xlsx')
s = [s for s in xl.sheet_names if 'Keyword' in s][0]
df = pd.read_excel(xl, sheet_name=s)
print("COLUMNS:", df.columns.tolist())
print("\nDATA HEAD:")
print(df.head(10).to_string())
print("\nKEYWORDS COLUMN SAMPLE:")
print(df['Keywords'].dropna().tolist()[:10])
