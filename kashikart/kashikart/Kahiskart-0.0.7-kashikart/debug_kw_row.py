import pandas as pd
df = pd.read_excel('uploads/All Source Web Links.xlsx', sheet_name='Search Keywords_Priority Rank', nrows=2)
for k, v in df.iloc[0].to_dict().items():
    print(f"KEY: {repr(k)} | VAL: {repr(v)}")
