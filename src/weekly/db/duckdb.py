import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from weekly.db.duckdb_schema import initialize_duckdb_schema


class DuckDBManager:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn: duckdb.DuckDBPyConnection | None = None

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(self._db_path))
        initialize_duckdb_schema(self._conn)

    @contextmanager
    def connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        with self._lock:
            if self._conn is None:
                self._conn = duckdb.connect(str(self._db_path))
            yield self._conn

    # Keep these as aliases for clarity in calling code
    read_connection = connection
    write_connection = connection

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
