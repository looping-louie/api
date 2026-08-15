"""Unit tests for SQLite migration checksum handling."""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from pathlib import Path

from src.app.repositories.infrastructure.migration_runner import (
    run_sqlite_migrations,
)


def test_migration_checksum_uses_exact_file_bytes(
    tmp_path: Path,
) -> None:
    """Persist the checksum calculated from the migration file bytes."""

    migration_bytes = b'CREATE TABLE examples (id TEXT);\n'
    migrations_path = tmp_path / 'migrations'
    migrations_path.mkdir()
    (migrations_path / '0001_examples.sql').write_bytes(
        migration_bytes,
    )
    database_path = tmp_path / 'database.sqlite'

    asyncio.run(
        run_sqlite_migrations(
            database_path=database_path,
            migrations_path=migrations_path,
        )
    )

    connection = sqlite3.connect(database_path)
    checksum = connection.execute(
        'SELECT checksum FROM schema_migrations'
    ).fetchone()
    connection.close()

    assert checksum == (
        hashlib.sha256(migration_bytes).hexdigest(),
    )
