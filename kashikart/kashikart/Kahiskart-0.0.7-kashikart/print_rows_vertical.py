import pandas as pd
df = pd.read_excel('uploads/All Source Web Links.xlsx', sheet_name='Source Links FL WA OR', nrows=10)
for i, row in df.iterrows():
    print(f"ROW {i}:")
    for j, val in enumerate(row):
        print(f"  Col {j} ({df.columns[j]}): {val}")
    print("-" * 20)
