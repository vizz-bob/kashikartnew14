from openpyxl import load_workbook


def load_excel(path: str):
    """
    Opens Excel in read-only mode.
    """
    wb = load_workbook(
        filename=path,
        read_only=True,
        data_only=True
    )
    return wb
