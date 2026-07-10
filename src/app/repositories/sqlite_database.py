"""Shared asynchronous SQLite connection and schema management."""

import asyncio
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


class SqliteDatabase:
    """Own SQLite connections used by application repositories."""

    def __init__(self, database_path: Path) -> None:
        """Store the database path and schema initialisation state."""

        self._database_path = database_path
        self._schema_lock = asyncio.Lock()
        self._ready_schemas: set[str] = set()

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

    async def ensure_schema(
        self,
        schema_name: str,
        statements: Iterable[str],
    ) -> None:
        """Apply one idempotent repository schema once per process."""

        if schema_name in self._ready_schemas:
            return

        async with self._schema_lock:
            if schema_name in self._ready_schemas:
                return

            async with self.connect() as connection:
                for statement in statements:
                    await connection.execute(statement)

                await connection.commit()

            self._ready_schemas.add(schema_name)
