import os
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SQL_QUERY = """
SELECT * FROM `process_result`
"""

OUTPUT_FILE_PATH = BASE_DIR / "result.csv"


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


def append_query_to_csv(connection, csv_path):

    try:
        print("Connected to MySQL successfully.")

        dataframe = pd.read_sql_query(
            SQL_QUERY,
            connection
        )

        file_exists = os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0

        dataframe.to_csv(
            csv_path,
            mode="a",
            index=False,
            header=not file_exists  # only write header if file is new
        )

        print("Export completed successfully.")
        print(f"Rows appended: {len(dataframe)}")
        print(f"Output file: {csv_path}")

    except mysql.connector.Error as error:
        print(f"MySQL error: {error}")

    except PermissionError:
        print(
            "Permission denied. Make sure the CSV file is not open "
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
    append_query_to_csv(connection, OUTPUT_FILE_PATH)
