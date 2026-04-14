import pandas as pd
df = pd.read_excel('uploads/All Source Web Links.xlsx', sheet_name='All_in_One_Data_Format_WA_OR', nrows=5)
with open('debug_rows.txt', 'w') as f:
    f.write(str(df.columns.tolist()))
    f.write("\n\n")
    f.write(df.to_string())
