"""SQLite migration discovery and execution."""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from src.app.services.shared.settings import get_app_settings


DEFAULT_MIGRATIONS_PATH = (
    Path(__file__).resolve().parents[4]
    / "migrations"
    / "sqlite"
)

MIGRATION_FILENAME_PATTERN = re.compile(
    r"^(?P<version>\d{4}_[a-z0-9_]+)\.sql$"
)


class MigrationError(RuntimeError):
    """Base error raised while discovering or applying migrations."""


class MigrationDirectoryNotFoundError(MigrationError):
    """Raised when the configured migration directory does not exist."""


class InvalidMigrationFilenameError(MigrationError):
    """Raised when a SQL migration has an unsupported filename."""


class MigrationChecksumMismatchError(MigrationError):
    """Raised when an applied migration has subsequently changed."""


class MigrationExecutionError(MigrationError):
    """Raised when SQLite cannot apply a migration."""


@dataclass(frozen=True, slots=True)
class Migration:
    """One immutable SQL migration loaded from disk."""

    version: str
    path: Path
    sql: str
    checksum: str


class SqliteMigrationRunner:
    """Applies pending SQLite migrations in filename order."""

    def __init__(
        self,
        *,
        database_path: Path,
        migrations_path: Path = DEFAULT_MIGRATIONS_PATH,
    ) -> None:
        """Store the database and migration source paths."""
        self._database_path = database_path
        self._migrations_path = migrations_path

    async def apply_pending(self) -> list[str]:
        """Apply every pending migration and return applied versions."""

        migrations = self._load_migrations()
        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        async with aiosqlite.connect(self._database_path) as connection:
            await connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            await self._ensure_migration_table(connection)

            applied_migrations = await self._load_applied_migrations(
                connection,
            )
            applied_versions: list[str] = []

            for migration in migrations:
                existing_checksum = applied_migrations.get(
                    migration.version,
                )

                if existing_checksum is not None:
                    self._validate_checksum(
                        migration=migration,
                        existing_checksum=existing_checksum,
                    )
                    continue

                await self._apply_migration(
                    connection=connection,
                    migration=migration,
                )
                applied_versions.append(migration.version)

            return applied_versions

    def _load_migrations(self) -> tuple[Migration, ...]:
        """Load and validate migration files in version order."""
        if not self._migrations_path.is_dir():
            raise MigrationDirectoryNotFoundError(
                "SQLite migration directory does not exist: "
                f"{self._migrations_path}"
            )

        migrations: list[Migration] = []

        for path in sorted(self._migrations_path.glob("*.sql")):
            match = MIGRATION_FILENAME_PATTERN.fullmatch(path.name)

            if match is None:
                raise InvalidMigrationFilenameError(
                    f"Invalid migration filename: {path.name}"
                )

            sql = path.read_text(encoding="utf-8")

            if not sql.strip():
                raise MigrationError(
                    f"Migration '{path.name}' is empty."
                )

            migrations.append(
                Migration(
                    version=match.group("version"),
                    path=path,
                    sql=sql,
                    checksum=self._calculate_checksum(sql),
                )
            )

        return tuple(migrations)

    @staticmethod
    async def _ensure_migration_table(
        connection: aiosqlite.Connection,
    ) -> None:
        """Create the migration tracking table when absent."""
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        await connection.commit()

    @staticmethod
    async def _load_applied_migrations(
        connection: aiosqlite.Connection,
    ) -> dict[str, str]:
        """Return applied migration checksums indexed by version."""
        cursor = await connection.execute(
            """
            SELECT
                version,
                checksum
            FROM schema_migrations
            """
        )
        rows = await cursor.fetchall()
        await cursor.close()

        return {
            str(version): str(checksum)
            for version, checksum in rows
        }

    async def _apply_migration(
        self,
        *,
        connection: aiosqlite.Connection,
        migration: Migration,
    ) -> None:
        """Apply one migration and record it atomically."""
        version_literal = self._sqlite_literal(
            migration.version,
        )
        checksum_literal = self._sqlite_literal(
            migration.checksum,
        )

        script = f"""
        BEGIN IMMEDIATE;

        {migration.sql.rstrip()}

        INSERT INTO schema_migrations (
            version,
            checksum,
            applied_at
        )
        VALUES (
            {version_literal},
            {checksum_literal},
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        );

        COMMIT;
        """

        try:
            await connection.executescript(script)
        except aiosqlite.Error as exc:
            await connection.rollback()

            raise MigrationExecutionError(
                f"Failed to apply migration "
                f"'{migration.version}' from '{migration.path}'."
            ) from exc

    @staticmethod
    def _validate_checksum(
        *,
        migration: Migration,
        existing_checksum: str,
    ) -> None:
        """Reject a migration changed after its initial application."""
        if migration.checksum == existing_checksum:
            return

        raise MigrationChecksumMismatchError(
            f"Migration '{migration.version}' has changed after "
            "being applied."
        )

    @staticmethod
    def _calculate_checksum(sql: str) -> str:
        """Calculate the stable SHA-256 checksum for migration SQL."""
        return hashlib.sha256(
            sql.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _sqlite_literal(value: str) -> str:
        """Quote a trusted string as a SQLite literal."""
        escaped = value.replace(
            "'",
            "''",
        )
        return f"'{escaped}'"


async def run_sqlite_migrations(
    *,
    database_path: Path,
    migrations_path: Path = DEFAULT_MIGRATIONS_PATH,
) -> list[str]:
    """Convenience entry point for applying SQLite migrations."""

    runner = SqliteMigrationRunner(
        database_path=database_path,
        migrations_path=migrations_path,
    )

    return await runner.apply_pending()


def main() -> None:
    """Run SQLite migrations using application settings."""

    settings = get_app_settings()

    applied = asyncio.run(
        run_sqlite_migrations(
            database_path=settings.database_path,
        )
    )

    if applied:
        print(
            "Applied migrations: "
            + ", ".join(applied)
        )
        return

    print("No pending migrations.")


if __name__ == "__main__":
    main()
