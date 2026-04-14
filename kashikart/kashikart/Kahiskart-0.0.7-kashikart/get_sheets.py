import pandas as pd
xl = pd.ExcelFile('uploads/All Source Web Links.xlsx')
with open('all_sheet_names.txt', 'w') as f:
    f.write('\n'.join(xl.sheet_names))
