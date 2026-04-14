import pandas as pd
df = pd.read_excel('uploads/All Source Web Links.xlsx', sheet_name='All_in_One_Data_Format_WA_OR', nrows=100)
for col in df.columns:
    non_null = df[col].dropna().unique()
    print(f"Column '{col}' has {len(non_null)} unique values. Sample: {non_null[:5]}")
