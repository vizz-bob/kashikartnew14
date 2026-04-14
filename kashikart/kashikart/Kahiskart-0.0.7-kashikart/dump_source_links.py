import pandas as pd
df = pd.read_excel('uploads/All Source Web Links.xlsx', sheet_name='Source Links FL WA OR', nrows=10)
with open('source_links_debug.txt', 'w') as f:
    f.write(df.to_string())
