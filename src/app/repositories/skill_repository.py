"""SQLite persistence for custom skills and built-in overrides."""

import json
from datetime import datetime
from typing import Protocol

import aiosqlite

from src.app.models.skills import StoredSkill
from src.app.repositories.sqlite_database import SqliteDatabase


class SkillRepository(Protocol):
    """Persistence operations required by SkillService."""

    async def list_for_org(self, org_id: str) -> list[StoredSkill]:
        """Return all stored rows, including deleted rows."""

    async def get(
        self,
        org_id: str,
        skill_id: str,
    ) -> StoredSkill | None:
        """Return one stored skill row."""

    async def upsert(self, skill: StoredSkill) -> StoredSkill:
        """Create or replace one stored skill row."""

    async def mark_deleted(
        self,
        org_id: str,
        skill_id: str,
        updated_by: str,
        updated_at: datetime,
    ) -> StoredSkill:
        """Soft-delete one stored skill row."""

    async def restore_custom(
        self,
        org_id: str,
        skill_id: str,
        updated_by: str,
        updated_at: datetime,
    ) -> StoredSkill:
        """Restore one soft-deleted custom skill."""

    async def hard_delete(
        self,
        org_id: str,
        skill_id: str,
    ) -> None:
        """Permanently remove one built-in override row."""


class SqliteSkillRepository:
    """SQLite implementation of SkillRepository."""

    _SCHEMA = (
        """
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('custom', 'override')),
            base_skill_id TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT,
            UNIQUE(org_id, skill_id)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_skills_org_source
        ON skills(org_id, source)
        """,
    )

    def __init__(self, database: SqliteDatabase) -> None:
        """Store the shared database dependency."""

        self._database = database

    async def list_for_org(self, org_id: str) -> list[StoredSkill]:
        """Return all stored rows, including deleted rows."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                SELECT *
                FROM skills
                WHERE org_id = ?
                ORDER BY skill_id
                """,
                (org_id,),
            )
            rows = await cursor.fetchall()

        return [self._row_to_skill(row) for row in rows]

    async def get(
        self,
        org_id: str,
        skill_id: str,
    ) -> StoredSkill | None:
        """Return one stored skill row."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                SELECT *
                FROM skills
                WHERE org_id = ? AND skill_id = ?
                """,
                (org_id, skill_id),
            )
            row = await cursor.fetchone()

        return self._row_to_skill(row) if row is not None else None

    async def upsert(self, skill: StoredSkill) -> StoredSkill:
        """Create or replace one stored skill row."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            await connection.execute(
                """
                INSERT INTO skills (
                    id,
                    org_id,
                    skill_id,
                    name,
                    description,
                    content,
                    metadata_json,
                    source,
                    base_skill_id,
                    created_by,
                    created_at,
                    updated_by,
                    updated_at,
                    deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(org_id, skill_id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    content = excluded.content,
                    metadata_json = excluded.metadata_json,
                    source = excluded.source,
                    base_skill_id = excluded.base_skill_id,
                    updated_by = excluded.updated_by,
                    updated_at = excluded.updated_at,
                    deleted_at = excluded.deleted_at
                """,
                self._skill_values(skill),
            )
            await connection.commit()

        stored = await self.get(skill.org_id, skill.skill_id)

        if stored is None:
            raise RuntimeError("Skill was not persisted.")

        return stored

    async def mark_deleted(
        self,
        org_id: str,
        skill_id: str,
        updated_by: str,
        updated_at: datetime,
    ) -> StoredSkill:
        """Soft-delete one stored skill row."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                UPDATE skills
                SET updated_by = ?,
                    updated_at = ?,
                    deleted_at = ?
                WHERE org_id = ? AND skill_id = ?
                """,
                (
                    updated_by,
                    updated_at.isoformat(),
                    updated_at.isoformat(),
                    org_id,
                    skill_id,
                ),
            )
            await connection.commit()

        if cursor.rowcount == 0:
            raise KeyError(f"Skill '{skill_id}' does not exist.")

        stored = await self.get(org_id, skill_id)

        if stored is None:
            raise RuntimeError("Deleted skill could not be reloaded.")

        return stored

    async def restore_custom(
        self,
        org_id: str,
        skill_id: str,
        updated_by: str,
        updated_at: datetime,
    ) -> StoredSkill:
        """Restore one soft-deleted custom skill."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                UPDATE skills
                SET updated_by = ?,
                    updated_at = ?,
                    deleted_at = NULL
                WHERE org_id = ? AND skill_id = ? AND source = 'custom'
                """,
                (
                    updated_by,
                    updated_at.isoformat(),
                    org_id,
                    skill_id,
                ),
            )
            await connection.commit()

        if cursor.rowcount == 0:
            raise KeyError(
                f"Custom skill '{skill_id}' cannot be restored."
            )

        stored = await self.get(org_id, skill_id)

        if stored is None:
            raise RuntimeError("Restored skill could not be reloaded.")

        return stored

    async def hard_delete(
        self,
        org_id: str,
        skill_id: str,
    ) -> None:
        """Permanently remove one built-in override row."""

        await self._ensure_schema()

        async with self._database.connect() as connection:
            await connection.execute(
                """
                DELETE FROM skills
                WHERE org_id = ? AND skill_id = ? AND source = 'override'
                """,
                (org_id, skill_id),
            )
            await connection.commit()

    async def _ensure_schema(self) -> None:
        """Create the skills schema when first used."""

        await self._database.ensure_schema(
            schema_name="skills",
            statements=self._SCHEMA,
        )

    @staticmethod
    def _skill_values(skill: StoredSkill) -> tuple:
        """Convert a domain model into SQLite values."""

        return (
            skill.id,
            skill.org_id,
            skill.skill_id,
            skill.name,
            skill.description,
            skill.content,
            json.dumps(
                skill.metadata,
                ensure_ascii=False,
                sort_keys=True,
            ),
            skill.source,
            skill.base_skill_id,
            skill.created_by,
            skill.created_at.isoformat(),
            skill.updated_by,
            skill.updated_at.isoformat(),
            (
                skill.deleted_at.isoformat()
                if skill.deleted_at is not None
                else None
            ),
        )

    @staticmethod
    def _row_to_skill(row: aiosqlite.Row) -> StoredSkill:
        """Convert one SQLite row into a domain model."""

        return StoredSkill(
            id=row["id"],
            org_id=row["org_id"],
            skill_id=row["skill_id"],
            name=row["name"],
            description=row["description"],
            content=row["content"],
            metadata=json.loads(row["metadata_json"]),
            source=row["source"],
            base_skill_id=row["base_skill_id"],
            created_by=row["created_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_by=row["updated_by"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            deleted_at=(
                datetime.fromisoformat(row["deleted_at"])
                if row["deleted_at"]
                else None
            ),
        )
