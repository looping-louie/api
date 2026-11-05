"""SQLite persistence for personal access tokens."""

from datetime import datetime

from src.models.personal_access_token import PersonalAccessToken
from src.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.repositories.shared.datetime import parse_datetime


class SqlitePersonalAccessTokenRepository:
    """Store opaque user-owned API token digests in SQLite."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared SQLite connection manager."""

        self._database = database

    async def create(self, token: PersonalAccessToken) -> PersonalAccessToken:
        """Persist one personal access token."""

        async with self._database.connect() as connection:
            await connection.execute(
                '''
                INSERT INTO personal_access_tokens (
                    id, user_id, name, token_hash, created_at, last_used_at,
                    expires_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    token.id, token.user_id, token.name, token.token_hash,
                    token.created_at.isoformat(),
                    token.last_used_at.isoformat() if token.last_used_at else None,
                    token.expires_at.isoformat() if token.expires_at else None,
                    token.revoked_at.isoformat() if token.revoked_at else None,
                ),
            )
            await connection.commit()
        return token

    async def list_for_user(self, *, user_id: str) -> list[PersonalAccessToken]:
        """Return all user-owned tokens ordered by creation time."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, user_id, name, token_hash, created_at, last_used_at,
                       expires_at, revoked_at
                FROM personal_access_tokens
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                ''',
                (user_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return [_to_token(row) for row in rows]

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> PersonalAccessToken | None:
        """Return the token matching one stored digest."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, user_id, name, token_hash, created_at, last_used_at,
                       expires_at, revoked_at
                FROM personal_access_tokens
                WHERE token_hash = ?
                ''',
                (token_hash,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_token(row) if row is not None else None

    async def get(self, *, token_id: str) -> PersonalAccessToken | None:
        """Return one personal access token by its durable identifier."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, user_id, name, token_hash, created_at, last_used_at,
                       expires_at, revoked_at
                FROM personal_access_tokens
                WHERE id = ?
                ''',
                (token_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        return _to_token(row) if row is not None else None

    async def mark_used(self, *, token_id: str, used_at: datetime) -> None:
        """Update the token's most recent successful authentication time."""

        async with self._database.connect() as connection:
            await connection.execute(
                '''
                UPDATE personal_access_tokens
                SET last_used_at = ?
                WHERE id = ?
                ''',
                (used_at.isoformat(), token_id),
            )
            await connection.commit()

    async def revoke(self, *, token_id: str, revoked_at: datetime) -> None:
        """Mark one token revoked without deleting its audit record."""

        async with self._database.connect() as connection:
            await connection.execute(
                '''
                UPDATE personal_access_tokens
                SET revoked_at = ?
                WHERE id = ? AND revoked_at IS NULL
                ''',
                (revoked_at.isoformat(), token_id),
            )
            await connection.commit()


def _to_token(row: object) -> PersonalAccessToken:
    """Map one SQLite row to a personal access-token domain record."""

    return PersonalAccessToken(
        id=row['id'],
        user_id=row['user_id'],
        name=row['name'],
        token_hash=row['token_hash'],
        created_at=parse_datetime(row['created_at']),
        last_used_at=(
            parse_datetime(row['last_used_at'])
            if row['last_used_at'] is not None
            else None
        ),
        expires_at=(
            parse_datetime(row['expires_at'])
            if row['expires_at'] is not None
            else None
        ),
        revoked_at=(
            parse_datetime(row['revoked_at'])
            if row['revoked_at'] is not None
            else None
        ),
    )
