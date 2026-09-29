import os
from pathlib import Path

import mysql.connector
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SQL_QUERY = """
SELECT * FROM `process_result`
"""

OUTPUT_FILE_PATH = BASE_DIR / "result.xlsx"
SHEET_NAME = "process_result"
TABLE_NAME = "ProcessResult"


def require_env(name, allow_empty=False):
    value = os.environ.get(name)

    if value is None or (not allow_empty and not value.strip()):
        raise RuntimeError(
            f"{name} environment variable has not been configured. "
            f"Add it to {BASE_DIR / '.env'}"
        )

    return value.strip()


MYSQL_HOST = require_env("MYSQL_HOST")
MYSQL_PORT = int(require_env("MYSQL_PORT"))
MYSQL_DATABASE = require_env("MYSQL_DATABASE")
MYSQL_USER = require_env("MYSQL_USER")
MYSQL_PASSWORD = require_env("MYSQL_PASSWORD", allow_empty=True)


def connect_to_mysql(host, port, database, user, password):
    return mysql.connector.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )


def _refresh_table_range(worksheet, table_name, num_columns, num_rows):
    """Set the table range to cover the header plus num_rows data rows."""
    last_col = get_column_letter(num_columns)
    last_row = num_rows + 1  # +1 for the header row
    worksheet.tables[table_name].ref = f"A1:{last_col}{last_row}"


def _create_table(worksheet, table_name, num_columns, num_rows):
    last_col = get_column_letter(num_columns)
    last_row = num_rows + 1  # +1 for the header row
    table = Table(displayName=table_name, ref=f"A1:{last_col}{last_row}")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium9",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    worksheet.add_table(table)


def append_query_to_xlsx(connection, xlsx_path):

    try:
        print("Connected to MySQL successfully.")

        dataframe = pd.read_sql_query(
            SQL_QUERY,
            connection
        )

        if dataframe.empty:
            print("Query returned no rows. Nothing to export.")
            return

        columns = list(dataframe.columns)
        rows = dataframe.itertuples(index=False, name=None)

        file_exists = os.path.isfile(xlsx_path) and os.path.getsize(xlsx_path) > 0

        if not file_exists:
            # Create a fresh workbook with a header row and a table.
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = SHEET_NAME

            worksheet.append(columns)
            for row in rows:
                worksheet.append(list(row))

            _create_table(worksheet, TABLE_NAME, len(columns), len(dataframe))
        else:
            # Append to the existing sheet/table.
            workbook = load_workbook(xlsx_path)

            if SHEET_NAME in workbook.sheetnames:
                worksheet = workbook[SHEET_NAME]
            else:
                worksheet = workbook.create_sheet(SHEET_NAME)
                worksheet.append(columns)

            for row in rows:
                worksheet.append(list(row))

            data_rows = worksheet.max_row - 1  # exclude header row
            if TABLE_NAME in worksheet.tables:
                _refresh_table_range(worksheet, TABLE_NAME, len(columns), data_rows)
            else:
                _create_table(worksheet, TABLE_NAME, len(columns), data_rows)

        workbook.save(xlsx_path)

        print("Export completed successfully.")
        print(f"Rows appended: {len(dataframe)}")
        print(f"Output file: {xlsx_path}")

    except mysql.connector.Error as error:
        print(f"MySQL error: {error}")

    except PermissionError:
        print(
            "Permission denied. Make sure the Excel file is not open "
            "and you have access to the output folder."
        )

    except Exception as error:
        print(f"Unexpected error: {error}")

    finally:
        if connection is not None and connection.is_connected():
            connection.close()
            print("MySQL connection closed.")


if __name__ == "__main__":
    connection = connect_to_mysql(
        MYSQL_HOST,
        MYSQL_PORT,
        MYSQL_DATABASE,
        MYSQL_USER,
        MYSQL_PASSWORD
    )
    append_query_to_xlsx(connection, OUTPUT_FILE_PATH)
