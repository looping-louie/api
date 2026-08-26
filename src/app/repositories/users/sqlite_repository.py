"""SQLite persistence for user identities."""

from __future__ import annotations

from src.app.models.user import UserDocument
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.shared.datetime import parse_datetime


class SqliteUserRepository:
    """Persist API user identities in SQLite."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared SQLite connection manager."""

        self._database = database

    async def get(self, *, user_id: str) -> UserDocument | None:
        """Return one persisted user identity."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, created_at, updated_at
                FROM users
                WHERE id = ?
                ''',
                (user_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_document(row) if row is not None else None

    async def create_if_absent(self, document: UserDocument) -> UserDocument:
        """Create a user or return the record already stored for its ID."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO users (id, created_at, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO NOTHING
                    ''',
                    (
                        document.id,
                        document.created_at.isoformat(),
                        document.updated_at.isoformat(),
                    ),
                )
                cursor = await connection.execute(
                    '''
                    SELECT id, created_at, updated_at
                    FROM users
                    WHERE id = ?
                    ''',
                    (document.id,),
                )
                try:
                    row = await cursor.fetchone()
                finally:
                    await cursor.close()
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        if row is None:
            raise RuntimeError('User creation did not return a stored user.')
        return _to_document(row)


def _to_document(row: object) -> UserDocument:
    """Map a SQLite user row to the domain document."""

    return UserDocument(
        id=row['id'],
        created_at=parse_datetime(row['created_at']),
        updated_at=parse_datetime(row['updated_at']),
    )