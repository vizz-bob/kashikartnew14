import pandas as pd
df = pd.read_excel('uploads/All Source Web Links.xlsx', sheet_name='Source Links FL WA OR')
row = df[df.iloc[:, 0] == 78].iloc[0]
with open('row_78.txt', 'w') as f:
    for i, val in enumerate(row):
        f.write(f"Col {i} ({df.columns[i]}): {val}\n")
