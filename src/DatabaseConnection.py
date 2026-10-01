import mysql.connector


class DatabaseConnection:
    """Thin wrapper around a MySQL connection with query helpers."""

    # region FIELDS
    __conn = None
    # endregion

    def __init__(
        self,
        host_address,
        port_address,
        database_name,
        database_user,
        database_password,
    ):
        self.__conn = mysql.connector.connect(
            host=host_address,
            port=port_address,
            database=database_name,
            user=database_user,
            password=database_password,
        )

    # region PUBLIC
    @property
    def connection(self):
        return self.__conn

    def is_connected(self) -> bool:
        return self.__conn is not None and self.__conn.is_connected()

    def query(self, sql_query: str, parameters: dict | None = None) -> list[dict]:
        """Run a SELECT and return the rows as a list of dicts."""
        cursor = self.__conn.cursor(dictionary=True)
        try:
            cursor.execute(sql_query, parameters or {})
            return cursor.fetchall()
        finally:
            cursor.close()

    def execute(self, sql_query: str, parameters: dict | None = None) -> int:
        """Run an INSERT/UPDATE/DELETE and return the affected row count."""
        cursor = self.__conn.cursor()
        try:
            cursor.execute(sql_query, parameters or {})
            self.__conn.commit()
            return cursor.rowcount
        finally:
            cursor.close()

    def close(self):
        if self.is_connected():
            self.__conn.close()
        self.__conn = None

    @staticmethod
    def append_parameter(sql_query: str, parameter: dict) -> tuple[str, dict]:
        """Append `AND key = %(key)s` clauses for each parameter.

        Returns the extended query and the merged parameter dict, so it can be
        passed straight to query()/execute().
        """
        clauses = "".join(f" AND {name} = %({name})s" for name in parameter)
        return sql_query + clauses, dict(parameter)
    # endregion

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __del__(self):
        # __del__ can run after a failed __init__, so guard against a missing attr.
        try:
            self.close()
        except Exception:
            pass
