import os
import pandas as pd
import openpyxl 

SOURCE_FOLDER_PATH = r"C:\Users\jsubagyo\OneDrive - Philip Morris International\SKT Digitalization - SKT - ID - General\01. Automation Process - (APRO Pillar)\02. IPC Monitoring\Automate\testing-source"
TARGET_EXCEL_PATH = r"C:\Users\jsubagyo\OneDrive - Philip Morris International\SKT Digitalization - SKT - ID - General\01. Automation Process - (APRO Pillar)\02. IPC Monitoring\Automate\testing-target\target.xlsx"
TARGET_EXCEL_SHEET_NAME = "report_results"

WEIGHTING_TEMPLATE = {"Inspection Date": [], "Batch ID": [], "Product":[],"Process Step":[]}

def check_excel_opened(excel_path:str)->bool:
    try:
        with pd.ExcelWriter(excel_path, mode='a', engine='openpyxl') as writer:
            pass
        return False
    except PermissionError:
        raise PermissionError("Excel file is opened, please close the file first so the processc can continue.")
    
def inject_excel(excel_path: str, sheet_name: str, data: pd.DataFrame) -> None:
    if data.empty:
        return

    if not os.path.exists(excel_path):
        data.to_excel(
            excel_path,
            index=False,
            sheet_name=sheet_name
        )
        return
    check_excel_opened(excel_path)
    workbook = openpyxl.load_workbook(excel_path)

    if sheet_name in workbook.sheetnames:
        worksheet = workbook[sheet_name]
        start_row = worksheet.max_row
        write_header = False
    else:
        start_row = 0
        write_header = True
    workbook.close()

    with pd.ExcelWriter(
        excel_path,
        mode="a",
        engine="openpyxl",
        if_sheet_exists="overlay"
    ) as writer:
        data.to_excel(
            writer,
            index=False,
            header=write_header,
            sheet_name=sheet_name,
            startrow=start_row
        )

def load_all_excel_files(folder_path:str,template:dict)->pd.DataFrame:
    df = pd.DataFrame(template)
    for file in os.listdir(folder_path):
        if file.endswith(".xlsx") or file.endswith(".xls"):
            file_path = os.path.join(folder_path, file)
            temp_df = pd.read_excel(file_path)
            df = pd.concat([df, temp_df], ignore_index=True)
    return df

def main(source_folder_path:str,target_excel_path:str,target_excel_sheet_name:str,template:dict):
    data = load_all_excel_files(source_folder_path, template)
    inject_excel(target_excel_path, target_excel_sheet_name, data)


if __name__ == "__main__":
    main(SOURCE_FOLDER_PATH, TARGET_EXCEL_PATH, TARGET_EXCEL_SHEET_NAME, WEIGHTING_TEMPLATE)
