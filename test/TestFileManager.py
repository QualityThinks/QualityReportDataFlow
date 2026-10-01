import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from FileManager import FileManager

# The user's Excel file produced by the pipeline.
SOURCE_XLSX = PROJECT_ROOT / "output" / "test_users.xlsx"

# Target report folder: reports/2026/october
REPORT_DIR = PROJECT_ROOT / "reports" / "2026" / "october"


def main():
    print("TEST FILE MANAGER - move Excel file to reports/2026/october")

    if not FileManager.is_file(SOURCE_XLSX):
        print(f"Source Excel file not found: {SOURCE_XLSX}")
        return

    # Make sure the destination folder exists.
    FileManager.create_folder(REPORT_DIR)

    # Avoid overwriting a report that was already moved there.
    destination = FileManager.unique_destination(REPORT_DIR / SOURCE_XLSX.name)

    moved_to = FileManager.move(SOURCE_XLSX, destination)

    print(f"Moved: {SOURCE_XLSX}")
    print(f"    -> {moved_to}")
    print(f"Exists at destination: {FileManager.is_file(moved_to)}")
    print(f"Files in report folder: {[p.name for p in FileManager.list_files(REPORT_DIR)]}")


if __name__ == "__main__":
    main()
