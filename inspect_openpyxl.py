import openpyxl

def inspect_excel():
    wb = openpyxl.load_workbook('c:/Users/Rekha/OneDrive/Desktop/Dataset-LuminaAI-20260502T121105Z-3-001/Dataset-LuminaAI/NEET-Biology.xlsx', data_only=True)
    sheet = wb.active
    
    headers = [cell.value for cell in sheet[1]]
    print("Headers:", headers)
    
    # print first row of data
    first_row = [cell.value for cell in sheet[2]]
    print("First row data:", first_row)

if __name__ == "__main__":
    inspect_excel()
