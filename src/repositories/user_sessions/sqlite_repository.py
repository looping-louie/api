"""SQLite persistence for server-side user sessions."""

from src.models.user_session import UserSession
from src.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.repositories.shared.datetime import parse_datetime


class SqliteUserSessionRepository:
    """Store opaque browser-session digests in SQLite."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared SQLite connection manager."""

        self._database = database

    async def create(self, session: UserSession) -> UserSession:
        """Persist one session."""

        async with self._database.connect() as connection:
            await connection.execute(
                '''
                INSERT INTO user_sessions (
                    id, user_id, token_hash, created_at, last_seen_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    session.id, session.user_id, session.token_hash,
                    session.created_at.isoformat(), session.last_seen_at.isoformat(),
                    session.expires_at.isoformat(),
                ),
            )
            await connection.commit()
        return session

    async def get_by_token_hash(self, *, token_hash: str) -> UserSession | None:
        """Return one session selected by its digest."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, user_id, token_hash, created_at, last_seen_at, expires_at
                FROM user_sessions WHERE token_hash = ?
                ''',
                (token_hash,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        if row is None:
            return None
        return UserSession(
            id=row['id'], user_id=row['user_id'], token_hash=row['token_hash'],
            created_at=parse_datetime(row['created_at']),
            last_seen_at=parse_datetime(row['last_seen_at']),
            expires_at=parse_datetime(row['expires_at']),
        )

    async def delete_by_token_hash(self, *, token_hash: str) -> None:
        """Revoke one session selected by its digest."""

        async with self._database.connect() as connection:
            await connection.execute(
                'DELETE FROM user_sessions WHERE token_hash = ?',
                (token_hash,),
            )
            await connection.commit()

    async def delete_by_user_id(self, *, user_id: str) -> None:
        """Revoke every persisted browser session for one user."""

        async with self._database.connect() as connection:
            await connection.execute(
                'DELETE FROM user_sessions WHERE user_id = ?',
                (user_id,),
            )
            await connection.commit()
