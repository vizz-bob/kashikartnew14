import pandas as pd
df = pd.read_excel('uploads/All Source Web Links.xlsx', sheet_name='Source Links FL WA OR', nrows=5)
print("COLUMNS FOUND:")
for i, col in enumerate(df.columns):
    print(f"{i}: {col}")

print("\nDATA SAMPLE:")
print(df.iloc[:3].to_dict(orient='records'))
