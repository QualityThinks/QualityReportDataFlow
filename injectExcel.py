import os
import pandas as pd

SOURCE_FOLDER_PATH = "C:/QR/"
TARGET_EXCEL_PATH = "C:/QualityReport/QualityReport.xlsx"

WEIGHTING_TEMPLATE = {"":""}


def inject_excel(excel_path:str,data:pd.DataFrame):
    if os.path.exists(excel_path):
        with pd.ExcelWriter(excel_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
            data.to_excel(writer, index=False, sheet_name='report_results')
    else:
        data.to_excel(excel_path, index=False, sheet_name='report_results')

def load_all_excel_files(folder_path:str,template:dict)->pd.DataFrame:
    df = pd.DataFrame(template)
    for file in os.listdir(folder_path):
        if file.endswith(".xlsx") or file.endswith(".xls"):
            file_path = os.path.join(folder_path, file)
            temp_df = pd.read_excel(file_path)
            df = pd.concat([df, temp_df], ignore_index=True)
    return df

def main(source_folder_path:str,target_excel_path:str,template:dict):
    data = load_all_excel_files(source_folder_path, template)
    inject_excel(target_excel_path, data)


if __name__ == "__main__":
    main(SOURCE_FOLDER_PATH, TARGET_EXCEL_PATH, WEIGHTING_TEMPLATE)
