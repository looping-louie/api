"""Shared asynchronous SQLite connection management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


class SqliteDatabase:
    """Own SQLite connections used by application repositories."""

    def __init__(self, database_path: Path) -> None:
        """Store the database path."""

        self._database_path = database_path

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Open a configured SQLite connection."""

        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        connection = await aiosqlite.connect(self._database_path)
        connection.row_factory = aiosqlite.Row

        try:
            await connection.execute("PRAGMA foreign_keys = ON")
            await connection.execute("PRAGMA journal_mode = WAL")
            yield connection
        finally:
            await connection.close()
