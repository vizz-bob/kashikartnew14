import pandas as pd
df = pd.read_excel('uploads/All Source Web Links.xlsx', sheet_name='Source Links FL WA OR', nrows=1)
with open('columns_exact.txt', 'w') as f:
    f.write(str(list(df.columns)))
