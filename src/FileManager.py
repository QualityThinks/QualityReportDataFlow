import shutil
from pathlib import Path


class FileManager:
    """Helpers for common file-system operations (move, copy, delete, folders)."""

    #region PATHS
    @staticmethod
    def exists(path: str | Path) -> bool:
        """Return True if the given file or folder exists."""
        return Path(path).exists()

    @staticmethod
    def is_file(path: str | Path) -> bool:
        return Path(path).is_file()

    @staticmethod
    def is_folder(path: str | Path) -> bool:
        return Path(path).is_dir()
    #endregion

    #region FOLDERS
    @staticmethod
    def create_folder(folder_path: str | Path) -> Path:
        """Create a folder (and any missing parents). Returns its Path.

        Does nothing if the folder already exists.
        """
        folder = Path(folder_path)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    @staticmethod
    def list_files(folder_path: str | Path, pattern: str = "*") -> list[Path]:
        """Return the files directly inside a folder matching a glob pattern."""
        folder = Path(folder_path)
        if not folder.is_dir():
            raise NotADirectoryError(f"Not a folder: {folder}")
        return sorted(path for path in folder.glob(pattern) if path.is_file())
    #endregion

    #region FILE OPERATIONS
    @staticmethod
    def move(original_path: str | Path, destination_path: str | Path) -> Path:
        """Move a file (or folder) to a new location.

        The destination's parent folder is created if it does not exist.
        Returns the final destination Path.
        """
        source = Path(original_path)
        if not source.exists():
            raise FileNotFoundError(f"Source does not exist: {source}")

        destination = Path(destination_path)
        parent = destination.parent if destination.suffix else destination
        parent.mkdir(parents=True, exist_ok=True)

        return Path(shutil.move(str(source), str(destination)))

    @staticmethod
    def copy(original_path: str | Path, destination_path: str | Path) -> Path:
        """Copy a file to a new location, creating parent folders as needed.

        Returns the destination Path.
        """
        source = Path(original_path)
        if not source.is_file():
            raise FileNotFoundError(f"Source file does not exist: {source}")

        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        return Path(shutil.copy2(str(source), str(destination)))

    @staticmethod
    def delete(path: str | Path, missing_ok: bool = True) -> None:
        """Delete a file or folder. No error if it is already gone (missing_ok)."""
        target = Path(path)
        if not target.exists():
            if missing_ok:
                return
            raise FileNotFoundError(f"Path does not exist: {target}")

        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    @staticmethod
    def unique_destination(destination_path: str | Path) -> Path:
        """Return a non-colliding path by appending _001, _002, ... if needed."""
        destination = Path(destination_path)
        if not destination.exists():
            return destination

        counter = 1
        while True:
            candidate = destination.with_name(
                f"{destination.stem}_{counter:03d}{destination.suffix}"
            )
            if not candidate.exists():
                return candidate
            counter += 1
    #endregion
