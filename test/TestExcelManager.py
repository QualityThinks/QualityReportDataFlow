import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from EnvManager import EnvManager
from DatabaseConnection import DatabaseConnection
from ExcelManager import ExcelManager
from EncryptionManager import EncryptionManagerFactory

SQL_QUERY = "SELECT * FROM users"
SHEET_NAME = "users"
TABLE_NAME = "Users"

OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_XLSX = OUTPUT_DIR / "test_users.xlsx"


def load_environment() -> EnvManager:
    return EnvManager(PROJECT_ROOT / ".env")


def connect_to_mysql_database(env: EnvManager) -> DatabaseConnection:
    host_address = env.require("MYSQL_HOST")
    port_address = env.require("MYSQL_PORT")
    database = env.require("MYSQL_DATABASE")
    user = env.require("MYSQL_USER")
    encryption = EncryptionManagerFactory.from_env(env)
    password = encryption.decrypt_text(env.require("MYSQL_PASSWORD"))
    
    return DatabaseConnection(host_address, port_address, database, user, password)


def main():
    env = load_environment()

    print("TEST DB CONNECTION")
    with connect_to_mysql_database(env) as dbconn:
        rows = dbconn.query(SQL_QUERY)

    if not rows:
        print("Query returned no rows. Nothing to write.")
        return

    dataframe = pd.DataFrame(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ExcelManager.write_dataframe_as_table(
        dataframe, OUTPUT_XLSX, SHEET_NAME, TABLE_NAME
    )

    print(f"Rows written: {len(dataframe)}")
    print(f"Columns: {list(dataframe.columns)}")
    print(f"Excel file: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
