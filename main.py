"""Quality report data flow.

1. Load .env
2. Connect to MySQL
3. Run SQL_QUERY
4. Process the query results
5. Write the result to an Excel file
6. Build an email with the Excel file attached
7. Send the email
8. Update the query cache after successful delivery
"""

import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from DatabaseConnection import DatabaseConnection
from EmailManager import EmailManager, EmailManagerFactory
from EncryptionManager import EncryptionManager, EncryptionManagerFactory
from EnvManager import EnvManager
from ExcelManager import ExcelManager
from FileManager import FileManager


# region CONFIG

JSON_PATH = PROJECT_ROOT / "cache.json"
DEFAULT_LAST_END_TIMESTAMP = "1970-01-01T00:00:00"

SQL_QUERY = """
SELECT *
FROM `daily_report`
WHERE `End` > %(last_end_timestamp)s
ORDER BY `End` ASC;
"""

SHEET_NAME = "users"
TABLE_NAME = "Users"
REPORT_NAME = "quality_report"

LIST_CC_EMAIL = [
    "mohammadfirman.fardiansyah@sampoerna.com",
]

EMAIL_SUBJECT_DEFAULT = (
    f"[QID] Quality Inspection Device - Rungkut 1 - Unit 1 - "
    f"{date.today():%Y-%m-%d}"
)

EMAIL_BODY = """\
<html>
  <body>
    <h1>Quality Inspection Device Report</h1>
    <p>Dear,</p>
    <p>Please find the latest quality inspection report attached.</p>
    <p>Total records: {row_count}</p>
    <br>
    <p>Regards,<br>Automation</p>
  </body>
</html>
"""

TARGET_CW = 2.02
TOLERANCE_CW = 0.14
TARGET_BE = 10.0
TOLERANCE_BE = 0.25
TARGET_ME = 8.0
TOLERANCE_ME = 0.25

SOURCE_NUMERIC_FEATURES = [
    "Avg CW [1]",
    "Avg CW [2]",
    "UB [1]",
    "UB [2]",
    "UB [3]",
    "UB [4]",
    "UB [5]",
    "UB [6]",
    "UH [1]",
    "UH [2]",
    "UH [3]",
    "UH [4]",
    "UH [5]",
    "UH [6]",
]

CALCULATED_NUMERIC_FEATURES = [
    "Avg Cw [First]",
    "Avg Cw [Second]",
    "Avg Cw",
    "Avg Dia Be",
    "Avg Dia Me",
    "In Spec Cw",
    "In Spec Be",
    "In Spec Me",
]

NULL_TEXT_VALUES = {
    "",
    "na",
    "n/a",
    "nan",
    "none",
    "null",
    "<na>",
    "nat",
    "-",
}

BE_SOURCE_COLUMNS = [
    "UB [1]",
    "UB [2]",
    "UB [3]",
    "UB [4]",
    "UB [5]",
    "UB [6]",
]

ME_SOURCE_COLUMNS = [
    "UH [1]",
    "UH [2]",
    "UH [3]",
    "UH [4]",
    "UH [5]",
    "UH [6]",
]

# endregion


def load_parameters(path: Path = JSON_PATH) -> dict[str, Any]:
    """Load cached SQL parameters."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(f"Cache file must contain a JSON object: {path}")

        return data

    except FileNotFoundError:
        return {}

    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in cache file {path}: {error}") from error


def update_cache(params: dict[str, Any], path: Path = JSON_PATH) -> None:
    """Write cache parameters atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(params, file, indent=4, ensure_ascii=False)

        temporary_path.replace(path)

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_environment() -> EnvManager:
    """Load environment variables from the project .env file."""
    return EnvManager(PROJECT_ROOT / ".env")


def connect_to_mysql_database(
    env: EnvManager,
    encryption: EncryptionManager,
) -> DatabaseConnection:
    """Create the MySQL database connection."""
    del encryption

    mysql_port = env.require("MYSQL_PORT")

    try:
        parsed_port = int(mysql_port)
    except (TypeError, ValueError) as error:
        raise ValueError("MYSQL_PORT must contain a valid integer.") from error

    return DatabaseConnection(
        env.require("MYSQL_HOST"),
        parsed_port,
        env.require("MYSQL_DATABASE"),
        env.require("MYSQL_USER"),
        env.get("MYSQL_PASSWORD", ""),
    )


def is_missing(value: Any) -> bool:
    """Return True when a scalar value should be considered missing."""
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip().lower() in NULL_TEXT_VALUES

    try:
        missing_result = pd.isna(value)

        if isinstance(missing_result, (bool, np.bool_)) and bool(missing_result):
            return True
    except (TypeError, ValueError):
        pass

    if isinstance(value, (int, float, np.integer, np.floating)):
        try:
            if not math.isfinite(float(value)):
                return True
        except (TypeError, ValueError, OverflowError):
            return True

    return False


def normalize_missing_value(value: Any) -> Any:
    """Normalize recognized missing values to pandas.NA."""
    return pd.NA if is_missing(value) else value


def to_nullable_float(value: Any) -> Any:
    """Convert one value to a float or return pandas.NA."""
    if is_missing(value):
        return pd.NA

    normalized_value = value.strip().replace(",", ".") if isinstance(value, str) else value

    try:
        numeric_value = pd.to_numeric(normalized_value, errors="coerce")
    except (TypeError, ValueError):
        return pd.NA

    if is_missing(numeric_value):
        return pd.NA

    try:
        float_value = float(numeric_value)
    except (TypeError, ValueError, OverflowError):
        return pd.NA

    return float_value if math.isfinite(float_value) else pd.NA


def convert_numeric_columns(
    dataframe: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """Convert existing DataFrame columns to nullable Float64 columns."""
    result = dataframe.copy()

    for column in columns:
        if column not in result.columns:
            continue

        normalized_values = (
            result[column]
            .astype("string")
            .str.strip()
            .str.replace(",", ".", regex=False)
        )

        null_mask = normalized_values.str.lower().isin(NULL_TEXT_VALUES)
        normalized_values = normalized_values.mask(null_mask, pd.NA)

        numeric_values = pd.to_numeric(normalized_values, errors="coerce")
        numeric_values = numeric_values.replace([np.inf, -np.inf], np.nan)
        result[column] = numeric_values.astype("Float64")

    return result


def normalize_dataframe_missing_values(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize infinite and textual missing values."""
    result = dataframe.copy().replace([np.inf, -np.inf], np.nan)

    for column in result.columns:
        if pd.api.types.is_object_dtype(result[column].dtype):
            result[column] = result[column].map(normalize_missing_value)

    return result


def get_row_value(row: pd.Series, column: str) -> Any:
    """Safely retrieve a row value."""
    if column not in row.index:
        return pd.NA

    return normalize_missing_value(row[column])


def get_numeric_row_value(row: pd.Series, column: str) -> Any:
    """Safely retrieve and convert a numeric row value."""
    return to_nullable_float(get_row_value(row, column))


def safe_divide(value: Any, divisor: Any) -> Any:
    """Divide two values safely, returning pandas.NA when invalid."""
    numeric_value = to_nullable_float(value)
    numeric_divisor = to_nullable_float(divisor)

    if is_missing(numeric_value) or is_missing(numeric_divisor):
        return pd.NA

    if numeric_divisor == 0:
        return pd.NA

    result = numeric_value / numeric_divisor
    return result if math.isfinite(result) else pd.NA


def safe_mean(values: Iterable[Any]) -> Any:
    """Calculate an average while excluding missing values."""
    valid_values: list[float] = []

    for value in values:
        numeric_value = to_nullable_float(value)

        if not is_missing(numeric_value):
            valid_values.append(float(numeric_value))

    if not valid_values:
        return pd.NA

    average = sum(valid_values) / len(valid_values)
    return average if math.isfinite(average) else pd.NA


def check_in_spec(value: Any, target: Any, tolerance: Any) -> Any:
    """Return whether a value is within specification, or NA if unavailable."""
    numeric_value = to_nullable_float(value)
    numeric_target = to_nullable_float(target)
    numeric_tolerance = to_nullable_float(tolerance)

    if (
        is_missing(numeric_value)
        or is_missing(numeric_target)
        or is_missing(numeric_tolerance)
    ):
        return pd.NA

    if numeric_tolerance < 0:
        raise ValueError("Tolerance cannot be negative.")

    minimum_value = numeric_target - numeric_tolerance
    maximum_value = numeric_target + numeric_tolerance
    return minimum_value <= numeric_value <= maximum_value


def calculate_in_spec_percentage(
    values: Iterable[Any],
    target: Any,
    tolerance: Any,
) -> Any:
    """Calculate percentage in specification, excluding missing values."""
    numeric_target = to_nullable_float(target)
    numeric_tolerance = to_nullable_float(tolerance)

    if is_missing(numeric_target) or is_missing(numeric_tolerance):
        return pd.NA

    if numeric_tolerance < 0:
        raise ValueError("Tolerance cannot be negative.")

    valid_values: list[float] = []

    for value in values:
        numeric_value = to_nullable_float(value)

        if not is_missing(numeric_value):
            valid_values.append(float(numeric_value))

    if not valid_values:
        return pd.NA

    in_spec_count = sum(
        check_in_spec(value, numeric_target, numeric_tolerance) is True
        for value in valid_values
    )

    percentage = (in_spec_count / len(valid_values)) * 100.0
    return percentage if math.isfinite(percentage) else pd.NA


def run_query(dbconn: DatabaseConnection) -> tuple[pd.DataFrame, Any]:
    """Run the query and return its DataFrame and newest End timestamp."""
    sql_parameters = load_parameters()
    last_end_timestamp = sql_parameters.get(
        "last_end_timestamp",
        DEFAULT_LAST_END_TIMESTAMP,
    )

    if is_missing(last_end_timestamp):
        last_end_timestamp = DEFAULT_LAST_END_TIMESTAMP

    rows = dbconn.query(
        SQL_QUERY,
        {"last_end_timestamp": last_end_timestamp},
    )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        return dataframe, pd.NaT

    dataframe = normalize_dataframe_missing_values(dataframe)
    dataframe = convert_numeric_columns(dataframe, SOURCE_NUMERIC_FEATURES)

    if "Start" in dataframe.columns:
        dataframe["Start"] = pd.to_datetime(dataframe["Start"], errors="coerce")

    if "End" in dataframe.columns:
        dataframe["End"] = pd.to_datetime(dataframe["End"], errors="coerce")
        newest_end_timestamp = dataframe["End"].max()
    else:
        newest_end_timestamp = pd.NaT

    return dataframe, newest_end_timestamp


def process_dataframe(
    dataframe: pd.DataFrame,
    env: EnvManager,
    report_datetime: datetime,
) -> pd.DataFrame:
    """Add calculated report columns while safely handling missing values."""
    if dataframe.empty:
        return dataframe.copy()

    plant = env.require("PLANT")
    location = env.require("LOCATION")
    group = env.require("GROUP")
    brand = env.require("BRAND")
    bagian = env.require("BAGIAN")
    date_today = report_datetime.strftime("%y%m%d")
    processed_rows: list[dict[str, Any]] = []

    for increment, (_, row) in enumerate(dataframe.iterrows(), start=1):
        avg_cw_first = safe_divide(get_numeric_row_value(row, "Avg CW [1]"), 3)
        avg_cw_second = safe_divide(get_numeric_row_value(row, "Avg CW [2]"), 3)
        avg_cw = safe_mean([avg_cw_first, avg_cw_second])

        be_values = [
            get_numeric_row_value(row, column)
            for column in BE_SOURCE_COLUMNS
        ]
        me_values = [
            get_numeric_row_value(row, column)
            for column in ME_SOURCE_COLUMNS
        ]

        new_row = {
            "Tanggapan ID": f"{date_today}-{increment:03d}",
            "Tanggal Pengiriman": report_datetime,
            "Tanggal Pemeriksaan": get_row_value(row, "Start"),
            "Plant/Reg": plant,
            "Location": location,
            "Group/Cell": group,
            "No Id Pekerja": get_row_value(row, "ID PPSKT"),
            "Brand": brand,
            "Bagian": bagian,
            "Avg Cw [First]": avg_cw_first,
            "Avg Cw [Second]": avg_cw_second,
            "Avg Cw": avg_cw,
            "Avg Dia Be": safe_mean(be_values),
            "Avg Dia Me": safe_mean(me_values),
            "In Spec Cw": calculate_in_spec_percentage(
                [avg_cw_first, avg_cw_second],
                TARGET_CW,
                TOLERANCE_CW,
            ),
            "In Spec Be": calculate_in_spec_percentage(
                be_values,
                TARGET_BE,
                TOLERANCE_BE,
            ),
            "In Spec Me": calculate_in_spec_percentage(
                me_values,
                TARGET_ME,
                TOLERANCE_ME,
            ),
        }

        original_columns = {
            column: normalize_missing_value(value)
            for column, value in row.to_dict().items()
            if column not in new_row
        }

        processed_rows.append({**new_row, **original_columns})

    processed_dataframe = pd.DataFrame(processed_rows)
    processed_dataframe = convert_numeric_columns(
        processed_dataframe,
        SOURCE_NUMERIC_FEATURES + CALCULATED_NUMERIC_FEATURES,
    )

    for datetime_column in [
        "Tanggal Pengiriman",
        "Tanggal Pemeriksaan",
        "Start",
        "End",
    ]:
        if datetime_column in processed_dataframe.columns:
            processed_dataframe[datetime_column] = pd.to_datetime(
                processed_dataframe[datetime_column],
                errors="coerce",
            )

    return processed_dataframe


def prepare_dataframe_for_excel(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert missing values to None so Excel cells appear blank."""
    excel_dataframe = dataframe.copy()
    excel_dataframe = excel_dataframe.replace([np.inf, -np.inf], np.nan)
    excel_dataframe = excel_dataframe.astype(object)
    return excel_dataframe.where(pd.notna(excel_dataframe), None)


def write_excel(dataframe: pd.DataFrame, now: datetime) -> Path:
    """Write the report DataFrame into an Excel table."""
    report_dir = FileManager.create_folder(
        PROJECT_ROOT
        / "reports"
        / str(now.year)
        / now.strftime("%B").lower()
    )

    xlsx_path = FileManager.unique_destination(
        report_dir / f"{REPORT_NAME}_{now:%Y%m%d_%H%M%S}.xlsx"
    )

    ExcelManager.write_dataframe_as_table(
        prepare_dataframe_for_excel(dataframe),
        xlsx_path,
        SHEET_NAME,
        TABLE_NAME,
    )

    return xlsx_path


def build_email(
    env: EnvManager,
    encryption: EncryptionManager,
    xlsx_path: Path,
    row_count: int,
) -> EmailManager:
    """Build the report email and attach the generated workbook."""
    email = EmailManagerFactory.from_env(env, encryption)
    email.set_to(env.require("EMAIL_RECIPIENT"))
    email.set_subject(env.get("EMAIL_SUBJECT", EMAIL_SUBJECT_DEFAULT))

    if LIST_CC_EMAIL:
        email.set_cc(LIST_CC_EMAIL)

    email.set_body(EMAIL_BODY.format(row_count=row_count))
    email.attach_file(xlsx_path)
    return email


def main() -> int:
    """Run the complete report workflow."""
    now = datetime.now()

    print("1) Loading .env")
    env = load_environment()
    encryption = EncryptionManagerFactory.from_env(env)

    print("2) Connecting to MySQL")
    with connect_to_mysql_database(env, encryption) as dbconn:
        print("3) Running query")
        source_dataframe, newest_end_timestamp = run_query(dbconn)

    if source_dataframe.empty:
        print("   Query returned no rows. Nothing to report.")
        return 0

    print("4) Processing query results")
    dataframe = process_dataframe(source_dataframe, env, now)

    if dataframe.empty:
        print("   No rows remained after processing.")
        return 0

    print(f"   {len(dataframe)} rows, {len(dataframe.columns)} columns")
    print(f"   Columns: {list(dataframe.columns)}")

    print("5) Writing Excel")
    xlsx_path = write_excel(dataframe, now)
    print(f"   Report: {xlsx_path}")

    print("6) Building email")
    email = build_email(env, encryption, xlsx_path, len(dataframe))
    print(f"   Recipients: {email.recipients}")

    print("7) Sending email")
    email.send()
    print("   Email sent.")

    if pd.notna(newest_end_timestamp):
        print("8) Updating query cache")
        update_cache({
            "last_end_timestamp": newest_end_timestamp.isoformat()
        })
        print(f"   Cache updated to: {newest_end_timestamp.isoformat()}")
    else:
        print("8) Cache not updated because no valid End timestamp was found.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print(f"Flow failed: {type(error).__name__}: {error}")
        # Uncomment during development for the complete traceback:
        # import traceback
        # traceback.print_exc()
        sys.exit(1)
