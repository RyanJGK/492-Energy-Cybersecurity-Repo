from __future__ import annotations

import os
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import psycopg
except Exception:  # library might not be installed in some environments
    psycopg = None  # type: ignore


class DB:
    def query_value(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:  # pragma: no cover - interface
        raise NotImplementedError

    def query_row(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Tuple]:  # pragma: no cover
        raise NotImplementedError

    def query_rows(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Tuple]:  # pragma: no cover
        raise NotImplementedError

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:  # pragma: no cover
        raise NotImplementedError


class DatabaseClient(DB):
    def __init__(self, dsn: Optional[str] = None, logger: Optional[logging.Logger] = None):
        if psycopg is None:
            raise RuntimeError("psycopg is required to use DatabaseClient")
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise ValueError("DATABASE_URL not set and DSN not provided")
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._conn = psycopg.connect(self.dsn)  # type: ignore
        self._conn.autocommit = True

    def query_value(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
            return row[0] if row else None

    def query_row(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Tuple]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()

    def query_rows(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Tuple]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or ())


class FakeDB(DB):
    """Simple in-memory fake for unit tests. Provide handlers per SQL id tag."""

    def __init__(self):
        self.handlers: Dict[str, Any] = {}
        self.executed: List[Tuple[str, Tuple[Any, ...]]] = []

    def when(self, key: str, return_value: Any) -> None:
        self.handlers[key] = return_value

    def _match_key(self, sql: str) -> Optional[str]:
        for k in self.handlers.keys():
            if k in sql:
                return k
        return None

    def query_value(self, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
        key = self._match_key(sql)
        if key is None:
            raise KeyError(f"No fake handler for SQL: {sql}")
        value = self.handlers[key]
        return value

    def query_row(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[Tuple]:
        key = self._match_key(sql)
        if key is None:
            raise KeyError(f"No fake handler for SQL: {sql}")
        value = self.handlers[key]
        return value

    def query_rows(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Tuple]:
        key = self._match_key(sql)
        if key is None:
            raise KeyError(f"No fake handler for SQL: {sql}")
        value = self.handlers[key]
        return value

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        self.executed.append((sql, tuple(params or ())))
