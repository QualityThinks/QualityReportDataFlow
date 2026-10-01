"""Quality report data flow.

    1. Load .env
    2. Connect to MySQL
    3. Run SQL_QUERY
    4. Write the result to an Excel file
    5. Build an email with the Excel file attached
    6. Send the email

Run from the project root:
    python main.py
"""

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd

from DatabaseConnection import DatabaseConnection
from EmailManager import EmailManager
from EncryptionManager import EncryptionManager, EncryptionManagerFactory
from EnvManager import EnvManager
from ExcelManager import ExcelManager
from FileManager import FileManager

#region CONFIG
SQL_QUERY = "SELECT * FROM users"
SQL_PARAMETERS: dict = {}

SHEET_NAME = "users"
TABLE_NAME = "Users"
REPORT_NAME = "quality_report"

EMAIL_SUBJECT_DEFAULT = "Quality Report"
EMAIL_BODY = """\
<html>
  <body>
    <h2>Quality Report</h2>
    <p>Hello,</p>
    <p>Please find the latest quality report attached ({row_count} rows).</p>
    <p>Regards,<br>Automation</p>
  </body>
</html>
"""
#endregion


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
        encryption.decrypt_text(env.require("MYSQL_PASSWORD")),
    )


# 3. Run the query
def run_query(dbconn: DatabaseConnection) -> pd.DataFrame:
    rows = dbconn.query(SQL_QUERY, SQL_PARAMETERS)
    return pd.DataFrame(rows)


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
def build_email(
    env: EnvManager,
    encryption: EncryptionManager,
    xlsx_path: Path,
    row_count: int,
) -> EmailManager:
    email = EmailManager(
        smtp_host=env.require("SMTP_HOST"),
        smtp_port=env.get_int("SMTP_PORT", 587),
        smtp_security=env.get("SMTP_SECURITY", "starttls"),
        smtp_user=env.get("SMTP_USER", "") or "",
        smtp_password=encryption.decrypt_text(env.require("SMTP_PASSWORD")),
        smtp_timeout=env.get_int("SMTP_TIMEOUT", 30),
        sender=env.require("EMAIL_SENDER"),
    )
    email.set_to(env.require("EMAIL_RECIPIENT"))
    email.set_subject(env.get("EMAIL_SUBJECT", EMAIL_SUBJECT_DEFAULT))
    email.set_body(EMAIL_BODY.format(row_count=row_count))
    email.attach_file(xlsx_path)
    return email


def main() -> int:
    now = datetime.now()

    print("1) Loading .env")
    env = load_environment()
    encryption = EncryptionManagerFactory.from_env(env)

    print("2) Connecting to MySQL")
    with connect_to_mysql_database(env, encryption) as dbconn:
        print("3) Running query")
        dataframe = run_query(dbconn)

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
        sys.exit(1)
