import os
from pathlib import Path
from dotenv import dotenv_values, load_dotenv


class EnvManager:
    """Loads a .env file and gives access to its variables."""

    #region FIELDS
    __env_file_path: Path
    __variable_names: list[str]
    __values: dict[str, str]
    #endregion

    def __init__(self, env_path: str | Path):
        self.__env_file_path = Path(env_path).resolve()

        if not self.__env_file_path.is_file():
            raise FileNotFoundError(f".env file not found: {self.__env_file_path}")

        self.__variable_names = []
        self.__values = {}

        load_dotenv(self.__env_file_path)
        self.__get_all_variable_names()
        self.__load_all_values()

    def __get_all_variable_names(self):
        self.__variable_names = list(dotenv_values(self.__env_file_path).keys())

    def __load_all_values(self):
        for name in self.__variable_names:
            # os.environ wins, so a real environment variable can override .env.
            value = os.environ.get(name)
            self.__values[name] = value.strip() if value is not None else ""

    #region PUBLIC
    @property
    def env_file_path(self) -> Path:
        return self.__env_file_path

    @property
    def variable_names(self) -> list[str]:
        return list(self.__variable_names)

    def get(self, name: str, default: str | None = None) -> str | None:
        """Return the value, or default if it is missing or empty."""
        value = self.__values.get(name, os.environ.get(name, "").strip())
        return value if value else default

    def require(self, name: str, allow_empty: bool = False) -> str:
        """Return the value, or raise if it is not configured."""
        if name not in self.__values and name not in os.environ:
            raise RuntimeError(
                f"{name} environment variable has not been configured. "
                f"Add it to {self.__env_file_path}"
            )

        value = self.__values.get(name, os.environ.get(name, "").strip())
        if not allow_empty and not value:
            raise RuntimeError(
                f"{name} is empty. Set a value for it in {self.__env_file_path}"
            )
        return value

    def get_int(self, name: str, default: int | None = None) -> int | None:
        value = self.get(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError as error:
            raise RuntimeError(f"{name} must be an integer, got '{value}'.") from error

    def to_dict(self) -> dict[str, str]:
        return dict(self.__values)
    #endregion
