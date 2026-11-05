"""SQLite persistence for runtime service accounts."""

from datetime import datetime

from src.models.service_account import ServiceAccount
from src.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.repositories.shared.datetime import parse_datetime


class SqliteServiceAccountRepository:
    """Store opaque runtime service-account digests in SQLite."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    async def create(self, account: ServiceAccount) -> ServiceAccount:
        async with self._database.connect() as connection:
            await connection.execute('BEGIN IMMEDIATE')
            try:
                await connection.execute(
                    '''INSERT INTO service_accounts (
                        id, administrator_id, name, token_hash, created_at,
                        last_used_at, expires_at, revoked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (account.id, account.administrator_id, account.name,
                     account.token_hash, account.created_at.isoformat(), None,
                     account.expires_at.isoformat() if account.expires_at else None,
                     None),
                )
                await connection.executemany(
                    '''INSERT INTO service_account_projects (
                        service_account_id, project_id, created_at
                    ) VALUES (?, ?, ?)''',
                    [(account.id, project_id, account.created_at.isoformat())
                     for project_id in account.project_ids],
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return account

    async def list_for_administrator(self, *, administrator_id: str) -> list[ServiceAccount]:
        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''SELECT id, administrator_id, name, token_hash, created_at,
                          last_used_at, expires_at, revoked_at
                   FROM service_accounts WHERE administrator_id = ?
                   ORDER BY created_at DESC, id DESC''',
                (administrator_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
            return [await self._to_account(connection, row) for row in rows]

    async def get(self, *, account_id: str) -> ServiceAccount | None:
        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''SELECT id, administrator_id, name, token_hash, created_at,
                          last_used_at, expires_at, revoked_at
                   FROM service_accounts WHERE id = ?''',
                (account_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            return await self._to_account(connection, row) if row else None

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> ServiceAccount | None:
        """Return one service account selected by credential digest."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''SELECT id, administrator_id, name, token_hash, created_at,
                          last_used_at, expires_at, revoked_at
                   FROM service_accounts WHERE token_hash = ?''',
                (token_hash,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            return await self._to_account(connection, row) if row else None

    async def mark_used(self, *, account_id: str, used_at: datetime) -> None:
        """Update the most recent successful service-account use."""

        async with self._database.connect() as connection:
            await connection.execute(
                'UPDATE service_accounts SET last_used_at = ? WHERE id = ?',
                (used_at.isoformat(), account_id),
            )
            await connection.commit()

    async def revoke(self, *, account_id: str, revoked_at: datetime) -> None:
        async with self._database.connect() as connection:
            await connection.execute(
                'UPDATE service_accounts SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL',
                (revoked_at.isoformat(), account_id),
            )
            await connection.commit()

    async def _to_account(self, connection, row) -> ServiceAccount:
        cursor = await connection.execute(
            'SELECT project_id FROM service_account_projects WHERE service_account_id = ? ORDER BY project_id',
            (row['id'],),
        )
        try:
            project_ids = tuple(item['project_id'] for item in await cursor.fetchall())
        finally:
            await cursor.close()
        return ServiceAccount(
            id=row['id'], administrator_id=row['administrator_id'], name=row['name'],
            token_hash=row['token_hash'], project_ids=project_ids,
            created_at=parse_datetime(row['created_at']),
            last_used_at=parse_datetime(row['last_used_at']) if row['last_used_at'] else None,
            expires_at=parse_datetime(row['expires_at']) if row['expires_at'] else None,
            revoked_at=parse_datetime(row['revoked_at']) if row['revoked_at'] else None,
        )
