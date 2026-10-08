"""Quality report data flow.

    1. Load .env
    2. Connect to MySQL
    3. Run SQL_QUERY
    4. Write the result to an Excel file
    5. Build an email with the Excel file attached
    6. Send the email

Run from the project root:
    python main.py

Gmail login uses OAuth2 (SMTP_AUTH = oauth2 in .env), no app password.
Run script\\create_oauth_token.py once to set it up.
"""

import sys
import json
import numpy as np
from datetime import date
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from DatabaseConnection import DatabaseConnection
from EmailManager import EmailManager, EmailManagerFactory
from EncryptionManager import EncryptionManager, EncryptionManagerFactory
from EnvManager import EnvManager
from ExcelManager import ExcelManager
from FileManager import FileManager

#region CONFIG
JSON_PATH = "cache.json"
SQL_QUERY = """
SELECT * FROM `daily_report`
WHERE end > %(last_end_timestamp)s;
"""
SQL_PARAMETERS: dict = {}

SHEET_NAME = "users"
TABLE_NAME = "Users"
REPORT_NAME = "quality_report"
LIST_CC_EMAIL = [
    "mohammadfirman.fardiansyah@sampoerna.com",
]

EMAIL_SUBJECT_DEFAULT = f"[QID] Quality Inspection Device - Rungkut 1 - Unit 1 - {date.today()}"
EMAIL_BODY = """\
<html>
  <body>
    <h1>Quality Inspection Device Report</h1>
    <p>Dear,</p>
    <p>Please find the latest quality inspection report attached.</p><br>
    <p>Regards,<br>Automation</p>
  </body>
</html>
"""

TARGET_CW = 2.02
TOLERANCE_CW = 0.14 
TARGET_BE = 10
TOLERANCE_BE = 0.25
TARGET_ME = 8
TOLERANCE_ME = 0.25
#endregion

def load_parameters(path: str = JSON_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("Cache JSON must contain an object.")
        return data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error


def update_cache(params: dict, path: str = JSON_PATH) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(params, file, indent=4)

# 1. Load ENV
def load_environment() -> EnvManager:
    return EnvManager(PROJECT_ROOT / ".env")


# 2. Connect to MySQL
def connect_to_mysql_database(env: EnvManager, encryption: EncryptionManager) -> DatabaseConnection:
    return DatabaseConnection(
        env.require("MYSQL_HOST"),
        env.require("MYSQL_PORT"),
        env.require("MYSQL_DATABASE"),
        env.require("MYSQL_USER"),
        env.get("MYSQL_PASSWORD",""),
    )


# 3. Run the query
def run_query(dbconn: DatabaseConnection) -> pd.DataFrame:
    sql_parameters = load_parameters()
    rows = dbconn.query(
        SQL_QUERY,
        sql_parameters
    )
    dataframe = pd.DataFrame(rows)
    
    if dataframe.empty or "End" not in dataframe.columns:
        return dataframe

    newest_end_timestamp = dataframe["End"].max()
    if pd.notna(newest_end_timestamp):
        update_cache({
            "last_end_timestamp": newest_end_timestamp.isoformat()
        })

    return dataframe


# 4. Make it into Excel (reports/<year>/<month>/quality_report_<timestamp>.xlsx)
def write_excel(dataframe: pd.DataFrame, now: datetime) -> Path:
    report_dir = FileManager.create_folder(
        PROJECT_ROOT / "reports" / str(now.year) / now.strftime("%B").lower()
    )
    xlsx_path = FileManager.unique_destination(
        report_dir / f"{REPORT_NAME}_{now:%Y%m%d_%H%M%S}.xlsx"
    )
    ExcelManager.write_dataframe_as_table(dataframe, xlsx_path, SHEET_NAME, TABLE_NAME)
    return xlsx_path


# 5. Build the email with the Excel attachment
#    SMTP settings and the login (SMTP_AUTH = oauth2 for Gmail, or password)
#    come from .env; the factory decrypts the stored secrets.
def build_email(
    env: EnvManager,
    encryption: EncryptionManager,
    xlsx_path: Path,
    row_count: int,
) -> EmailManager:
    email = EmailManagerFactory.from_env(env, encryption)
    email.set_to(env.require("EMAIL_RECIPIENT"))
    email.set_subject(env.get("EMAIL_SUBJECT", EMAIL_SUBJECT_DEFAULT))
    email.set_cc(LIST_CC_EMAIL)
    email.set_body(EMAIL_BODY.format(row_count=row_count))
    email.attach_file(xlsx_path)
    return email

def check_in_spec(
    value: float,
    target: float,
    tolerance: float
) -> bool:
    """
    Check whether a value is within the allowed target tolerance.

    Example:
        target = 10
        tolerance = 2
        valid range = 8 to 12
    """
    if pd.isna(value):
        return False

    minimum_value = target - tolerance
    maximum_value = target + tolerance

    return minimum_value <= value <= maximum_value


def calculate_in_spec_percentage(
    values: list[float],
    target: float,
    tolerance: float
) -> np.float32:
    """
    Calculate the percentage of values that are within specification.
    """
    valid_values = [
        value
        for value in values
        if not pd.isna(value)
    ]

    if not valid_values:
        return np.float32(0.0)

    in_spec_count = sum(
        check_in_spec(value, target, tolerance)
        for value in valid_values
    )

    percentage = (in_spec_count / len(valid_values)) * 100

    return np.float32(percentage)


def process_dataframe(
    df: pd.DataFrame,
    env
) -> pd.DataFrame:
    processed_rows = []
    date_today = datetime.now().strftime("%y%m%d")

    # Read environment variables once instead of reading them
    # repeatedly for every DataFrame row.
    plant = env.Require("PLANT")
    location = env.Require("LOCATION")
    group = env.Require("GROUP")
    brand = env.Require("BRAND")
    bagian = env.Require("BAGIAN")

    for increment, (_, row) in enumerate(df.iterrows(), start=1):

        # Calculate the average for each CW inspection.
        avg_cw_1 = np.float32(row["Avg CW [1]"] / 3)
        avg_cw_2 = np.float32(row["Avg CW [2]"] / 3)

        # Calculate the overall CW average.
        avg_cw = np.float32(
            np.mean([
                avg_cw_1,
                avg_cw_2,
            ])
        )

        # BE measurements
        be_values = [
            row["UB [1]"],
            row["UB [2]"],
            row["UB [3]"],
            row["UB [4]"],
            row["UB [5]"],
            row["UB [6]"],
        ]

        avg_dia_be = np.float32(
            np.nanmean(be_values)
        )

        # Replace these column names if your ME columns use
        # different names.
        me_values = [
            row["UM [1]"],
            row["UM [2]"],
            row["UM [3]"],
            row["UM [4]"],
            row["UM [5]"],
            row["UM [6]"],
        ]

        avg_dia_me = np.float32(
            np.nanmean(me_values)
        )

        new_row = {
            "Tanggapan ID": f"{date_today}-{increment:03d}",
            "Tanggal Pemeriksaan": row["Start"],
            "Plant/Reg": plant,
            "Location": location,
            "Group/Cell": group,
            "No Id Pekerja": row["ID PPSKT"],
            "Brand": brand,
            "Bagian": bagian,

            # New calculated CW columns
            "Avg Cw [1]": avg_cw_1,
            "Avg Cw [2]": avg_cw_2,
            "Avg Cw": avg_cw,

            # Diameter averages
            "Avg Dia Be": avg_dia_be,
            "Avg Dia Me": avg_dia_me,

            # In-spec percentages
            "% In Spec Cw": calculate_in_spec_percentage(
                values=[
                    avg_cw_1,
                    avg_cw_2,
                ],
                target=TARGET_CW,
                tolerance=TOLERANCE_CW,
            ),

            "% In Spec Be": calculate_in_spec_percentage(
                values=be_values,
                target=TARGET_BE,
                tolerance=TOLERANCE_BE,
            ),

            "% In Spec Me": calculate_in_spec_percentage(
                values=me_values,
                target=TARGET_ME,
                tolerance=TOLERANCE_ME,
            ),
        }

        # Put calculated columns first and retain all original columns
        # after them.
        #
        # Original columns with the same names as new columns are excluded
        # so that they do not overwrite the calculated results.
        original_columns = {
            column: value
            for column, value in row.to_dict().items()
            if column not in new_row
        }

        combined_row = {
            **new_row,
            **original_columns,
        }

        processed_rows.append(combined_row)

    return pd.DataFrame(processed_rows)

def main() -> int:
    now = datetime.now()

    print("1) Loading .env")
    env = load_environment()
    encryption = EncryptionManagerFactory.from_env(env)

    print("2) Connecting to MySQL")
    with connect_to_mysql_database(env, encryption) as dbconn:
        print("3) Running query")
        dataframe = run_query(dbconn)
        dataframe = process_dataframe(dataframe,env)

    if dataframe.empty:
        print("   Query returned no rows. Nothing to report.")
        return 0
    print(f"   {len(dataframe)} rows, columns: {list(dataframe.columns)}")

    print("4) Writing Excel")
    xlsx_path = write_excel(dataframe, now)
    print(f"   {xlsx_path}")

    print("5) Building email")
    email = build_email(env, encryption, xlsx_path, len(dataframe))
    print(f"   recipients: {email.recipients}")

    print("6) Sending email")
    email.send()
    print("   Email sent.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print(f"Flow failed: {type(error).__name__}: {error}")
        # import traceback
        # traceback.print_exc()
        sys.exit(1)
