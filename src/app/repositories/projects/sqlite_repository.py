"""SQLite persistence for projects."""

from __future__ import annotations

from datetime import datetime

from src.app.models.project import ProjectDocument
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase


class SqliteProjectRepository:
    """Store project metadata in SQLite."""

    def __init__(self, database: SqliteDatabase) -> None:
        """Initialize the repository with shared SQLite storage."""

        self._database = database

    async def create(
        self,
        *,
        project: ProjectDocument,
        owner_id: str,
    ) -> ProjectDocument:
        """Create a Project and an owner membership in one transaction."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                await connection.execute(
                    '''
                    INSERT INTO workspaces (id, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        project.id,
                        project.name,
                        project.created_at.isoformat(),
                        project.updated_at.isoformat(),
                    ),
                )
                await connection.execute(
                    '''
                    INSERT INTO workspace_memberships (
                        workspace_id, user_id, role, is_default, created_at
                    ) VALUES (
                        ?, ?, 'owner',
                        CASE WHEN EXISTS (
                            SELECT 1
                            FROM workspace_memberships
                            WHERE user_id = ? AND is_default = 1
                        ) THEN 0 ELSE 1 END,
                        ?
                    )
                    ''',
                    (
                        project.id,
                        owner_id,
                        owner_id,
                        project.created_at.isoformat(),
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return project

    async def list_for_user(self, *, user_id: str) -> list[ProjectDocument]:
        """Return every Project available to one User."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT w.id, w.name, w.created_at, w.updated_at
                FROM workspaces AS w
                INNER JOIN workspace_memberships AS membership
                    ON membership.workspace_id = w.id
                WHERE membership.user_id = ?
                ORDER BY membership.is_default DESC, w.created_at ASC, w.id ASC
                ''',
                (user_id,),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
        return [self._project_from_row(row) for row in rows]

    async def get_project(self, *, project_id: str) -> ProjectDocument:
        """Return one Project known to have an active membership."""

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                '''
                SELECT id, name, created_at, updated_at
                FROM workspaces
                WHERE id = ?
                ''',
                (project_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
        if row is None:
            raise RuntimeError('Project membership references no Project.')
        return self._project_from_row(row)

    async def update_project(
        self,
        *,
        project: ProjectDocument,
    ) -> ProjectDocument:
        """Persist mutable Project metadata."""

        async with self._database.connect() as connection:
            try:
                await connection.execute('BEGIN IMMEDIATE')
                cursor = await connection.execute(
                    '''
                    UPDATE workspaces
                    SET name = ?, updated_at = ?
                    WHERE id = ?
                    RETURNING id, name, created_at, updated_at
                    ''',
                    (
                        project.name,
                        project.updated_at.isoformat(),
                        project.id,
                    ),
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
            raise RuntimeError('Project update did not return a Project.')
        return self._project_from_row(row)

    @staticmethod
    def _project_from_row(row: object) -> ProjectDocument:
        """Deserialize one SQLite row to a Project document."""

        values = dict(row)  # type: ignore[arg-type]
        return ProjectDocument(
            id=str(values['id']),
            name=str(values['name']),
            created_at=datetime.fromisoformat(str(values['created_at'])),
            updated_at=datetime.fromisoformat(str(values['updated_at'])),
        )
