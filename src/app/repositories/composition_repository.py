"""SQLite persistence for councils and loops."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

import aiosqlite

from src.app.services.shared.composition_service import (
    CompositionDocument,
    CompositionSummary,
    CompositionType,
)


JsonObject = dict[str, Any]
DependencyRow = tuple[
    str,
    str,
    str,
    str,
    str,
    str,
    int,
]


class CompositionRepository(Protocol):
    """Persistence operations required by CompositionService."""

    async def list_summaries(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        search: str | None = None,
    ) -> list[CompositionSummary]:
        """Return composition summaries for one workspace and type."""
        ...

    async def get(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> CompositionDocument | None:
        """Return one complete composition."""
        ...

    async def create(
        self,
        document: CompositionDocument,
    ) -> CompositionDocument:
        """Persist one composition aggregate."""
        ...

    async def update(
        self,
        document: CompositionDocument,
        *,
        expected_version: int,
    ) -> CompositionDocument | None:
        """Update one composition using optimistic concurrency."""
        ...

    async def delete(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> bool:
        """Delete one composition and report whether it existed."""
        ...


class SqliteCompositionRepository:
    """Persists councils and loops as atomic SQLite aggregates."""

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self._database_path = Path(database_path)

    async def list_summaries(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        search: str | None = None,
    ) -> list[CompositionSummary]:
        """Return summaries for one workspace and composition type."""

        async with self._connect() as connection:

            normalized_search = search.strip().casefold() if search else None
            search_pattern = (
                f"%{normalized_search}%"
                if normalized_search is not None
                else None
            )

            cursor = await connection.execute(
                """
                SELECT
                    compositions.id,
                    compositions.name,
                    compositions.description,
                    compositions.version,
                    compositions.created_at,
                    compositions.updated_at,
                    COUNT(composition_items.position) AS item_count
                FROM compositions
                LEFT JOIN composition_items
                    ON composition_items.workspace_id = compositions.workspace_id
                AND composition_items.composition_id = compositions.id
                WHERE compositions.workspace_id = ?
                AND compositions.composition_type = ?
                AND (
                    ? IS NULL
                    OR compositions.name_key LIKE ?
                    OR LOWER(compositions.description) LIKE ?
                )
                GROUP BY compositions.id
                ORDER BY
                    compositions.name_key ASC,
                    compositions.id ASC
                """,
                (
                    workspace_id,
                    composition_type,
                    normalized_search,
                    search_pattern,
                    search_pattern,
                ),
            )

            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()

        return [
            self._to_summary(row)
            for row in rows
        ]

    async def get(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> CompositionDocument | None:
        """Return one complete composition aggregate."""

        async with self._connect() as connection:
            return await self._get_with_connection(
                connection=connection,
                workspace_id=workspace_id,
                composition_type=composition_type,
                composition_id=composition_id,
            )

    async def create(
        self,
        document: CompositionDocument,
    ) -> CompositionDocument:
        """Insert a composition, its items and its dependencies."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")

                await connection.execute(
                    """
                    INSERT INTO compositions (
                        id,
                        workspace_id,
                        composition_type,
                        name,
                        name_key,
                        description,
                        attributes_json,
                        version,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.id,
                        document.workspace_id,
                        document.composition_type,
                        document.name,
                        self._normalize_name(document.name),
                        document.description,
                        self._serialize_object(document.attributes),
                        document.version,
                        self._serialize_datetime(document.created_at),
                        self._serialize_datetime(document.updated_at),
                    ),
                )

                await self._insert_items(
                    connection=connection,
                    document=document,
                )
                await self._insert_dependencies(
                    connection=connection,
                    document=document,
                )

                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

        stored = await self.get(
            workspace_id=document.workspace_id,
            composition_type=document.composition_type,
            composition_id=document.id,
        )

        if stored is None:
            raise RuntimeError(
                "Composition was not persisted."
            )

        return stored

    async def update(
        self,
        document: CompositionDocument,
        *,
        expected_version: int,
    ) -> CompositionDocument | None:
        """
        Replace one composition when its current version matches.

        None means the composition was removed or changed concurrently.
        """

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")

                cursor = await connection.execute(
                    """
                    UPDATE compositions
                    SET
                        name = ?,
                        name_key = ?,
                        description = ?,
                        attributes_json = ?,
                        version = ?,
                        updated_at = ?
                    WHERE id = ?
                      AND workspace_id = ?
                      AND composition_type = ?
                      AND version = ?
                    """,
                    (
                        document.name,
                        self._normalize_name(document.name),
                        document.description,
                        self._serialize_object(document.attributes),
                        document.version,
                        self._serialize_datetime(document.updated_at),
                        document.id,
                        document.workspace_id,
                        document.composition_type,
                        expected_version,
                    ),
                )

                try:
                    updated = cursor.rowcount == 1
                finally:
                    await cursor.close()

                if not updated:
                    await connection.rollback()
                    return None

                await self._delete_items(
                    connection=connection,
                    workspace_id=document.workspace_id,
                    composition_id=document.id,
                )
                await self._delete_dependencies(
                    connection=connection,
                    workspace_id=document.workspace_id,
                    composition_type=document.composition_type,
                    composition_id=document.id,
                )

                await self._insert_items(
                    connection=connection,
                    document=document,
                )
                await self._insert_dependencies(
                    connection=connection,
                    document=document,
                )

                stored = await self._get_with_connection(
                    connection=connection,
                    workspace_id=document.workspace_id,
                    composition_type=document.composition_type,
                    composition_id=document.id,
                )

                await connection.commit()
                return stored
            except Exception:
                await connection.rollback()
                raise

    async def delete(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> bool:
        """Delete one composition aggregate."""

        async with self._connect() as connection:
            try:
                await connection.execute("BEGIN IMMEDIATE")

                cursor = await connection.execute(
                    """
                    DELETE FROM compositions
                    WHERE id = ?
                      AND workspace_id = ?
                      AND composition_type = ?
                    """,
                    (
                        composition_id,
                        workspace_id,
                        composition_type,
                    ),
                )

                try:
                    deleted = cursor.rowcount == 1
                finally:
                    await cursor.close()

                await connection.commit()
                return deleted
            except Exception:
                await connection.rollback()
                raise

    async def _get_with_connection(
        self,
        *,
        connection: aiosqlite.Connection,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> CompositionDocument | None:
        cursor = await connection.execute(
            """
            SELECT
                id,
                workspace_id,
                composition_type,
                name,
                description,
                attributes_json,
                version,
                created_at,
                updated_at
            FROM compositions
            WHERE id = ?
              AND workspace_id = ?
              AND composition_type = ?
            LIMIT 1
            """,
            (
                composition_id,
                workspace_id,
                composition_type,
            ),
        )

        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()

        if row is None:
            return None

        items = await self._load_items(
            connection=connection,
            workspace_id=workspace_id,
            composition_id=composition_id,
        )

        return self._to_document(
            row=row,
            items=items,
        )

    @staticmethod
    async def _load_items(
        *,
        connection: aiosqlite.Connection,
        workspace_id: str,
        composition_id: str,
    ) -> tuple[JsonObject, ...]:
        cursor = await connection.execute(
            """
            SELECT item_json
            FROM composition_items
            WHERE workspace_id = ?
              AND composition_id = ?
            ORDER BY position ASC
            """,
            (
                workspace_id,
                composition_id,
            ),
        )

        try:
            rows = await cursor.fetchall()
        finally:
            await cursor.close()

        return tuple(
            SqliteCompositionRepository._parse_object(
                row["item_json"],
                field_name="item_json",
            )
            for row in rows
        )

    @staticmethod
    async def _insert_items(
        *,
        connection: aiosqlite.Connection,
        document: CompositionDocument,
    ) -> None:
        if not document.items:
            return

        await connection.executemany(
            """
            INSERT INTO composition_items (
                workspace_id,
                composition_id,
                position,
                item_json
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    document.workspace_id,
                    document.id,
                    position,
                    SqliteCompositionRepository._serialize_object(item),
                )
                for position, item in enumerate(document.items)
            ],
        )

    @staticmethod
    async def _delete_items(
        *,
        connection: aiosqlite.Connection,
        workspace_id: str,
        composition_id: str,
    ) -> None:
        await connection.execute(
            """
            DELETE FROM composition_items
            WHERE workspace_id = ?
              AND composition_id = ?
            """,
            (
                workspace_id,
                composition_id,
            ),
        )

    async def _insert_dependencies(
        self,
        *,
        connection: aiosqlite.Connection,
        document: CompositionDocument,
    ) -> None:
        dependencies = self._extract_dependencies(document)

        if not dependencies:
            return

        await connection.executemany(
            """
            INSERT INTO resource_dependencies (
                workspace_id,
                source_type,
                source_id,
                target_type,
                target_id,
                relation,
                position
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            dependencies,
        )

    @staticmethod
    async def _delete_dependencies(
        *,
        connection: aiosqlite.Connection,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> None:
        await connection.execute(
            """
            DELETE FROM resource_dependencies
            WHERE workspace_id = ?
              AND source_type = ?
              AND source_id = ?
            """,
            (
                workspace_id,
                composition_type,
                composition_id,
            ),
        )

    def _extract_dependencies(
        self,
        document: CompositionDocument,
    ) -> list[DependencyRow]:
        if document.composition_type == "council":
            return self._extract_council_dependencies(document)

        if document.composition_type == "loop":
            return self._extract_loop_dependencies(document)

        return []

    def _extract_council_dependencies(
        self,
        document: CompositionDocument,
    ) -> list[DependencyRow]:
        dependencies: list[DependencyRow] = []

        for position, item in enumerate(document.items):
            persona_id = self._optional_string(
                item.get("persona_id"),
            )

            if persona_id is not None:
                dependencies.append(
                    (
                        document.workspace_id,
                        document.composition_type,
                        document.id,
                        "persona",
                        persona_id,
                        "assignment_persona",
                        position,
                    )
                )

            skill_ids = item.get("skill_ids", ())

            if not isinstance(skill_ids, Sequence) or isinstance(
                skill_ids,
                str,
            ):
                continue

            for skill_id_value in skill_ids:
                skill_id = self._optional_string(skill_id_value)

                if skill_id is None:
                    continue

                dependencies.append(
                    (
                        document.workspace_id,
                        document.composition_type,
                        document.id,
                        "skill",
                        skill_id,
                        "assignment_skill",
                        position,
                    )
                )

        return dependencies

    def _extract_loop_dependencies(
        self,
        document: CompositionDocument,
    ) -> list[DependencyRow]:
        dependencies: list[DependencyRow] = []

        council_id = self._optional_string(
            document.attributes.get("council_id"),
        )

        if council_id is not None:
            dependencies.append(
                (
                    document.workspace_id,
                    document.composition_type,
                    document.id,
                    "council",
                    council_id,
                    "loop_council",
                    0,
                )
            )

        for position, item in enumerate(document.items):
            model_id = self._optional_string(
                item.get("model_id"),
            )

            if model_id is None:
                continue

            dependencies.append(
                (
                    document.workspace_id,
                    document.composition_type,
                    document.id,
                    "model",
                    model_id,
                    "model_binding",
                    position,
                )
            )

        return dependencies

    @asynccontextmanager
    async def _connect(
        self,
    ) -> AsyncIterator[aiosqlite.Connection]:
        connection = await aiosqlite.connect(
            self._database_path,
        )

        try:
            connection.row_factory = aiosqlite.Row
            await connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            yield connection
        finally:
            await connection.close()

    @staticmethod
    def _to_summary(
        row: aiosqlite.Row,
    ) -> CompositionSummary:
        return CompositionSummary(
            id=str(row["id"]),
            name=str(row["name"]),
            description=str(row["description"]),
            item_count=int(row["item_count"]),
            version=int(row["version"]),
            created_at=SqliteCompositionRepository._parse_datetime(
                row["created_at"],
            ),
            updated_at=SqliteCompositionRepository._parse_datetime(
                row["updated_at"],
            ),
        )

    @staticmethod
    def _to_document(
        *,
        row: aiosqlite.Row,
        items: tuple[JsonObject, ...],
    ) -> CompositionDocument:
        return CompositionDocument(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            composition_type=cast(
                CompositionType,
                str(row["composition_type"]),
            ),
            name=str(row["name"]),
            description=str(row["description"]),
            attributes=SqliteCompositionRepository._parse_object(
                row["attributes_json"],
                field_name="attributes_json",
            ),
            items=items,
            version=int(row["version"]),
            created_at=SqliteCompositionRepository._parse_datetime(
                row["created_at"],
            ),
            updated_at=SqliteCompositionRepository._parse_datetime(
                row["updated_at"],
            ),
        )

    @staticmethod
    def _normalize_name(name: str) -> str:
        return " ".join(
            name.strip().casefold().split()
        )

    @staticmethod
    def _serialize_object(
        value: Mapping[str, Any],
    ) -> str:
        return json.dumps(
            dict(value),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _parse_object(
        value: object,
        *,
        field_name: str,
    ) -> JsonObject:
        parsed = json.loads(
            str(value),
        )

        if not isinstance(parsed, dict):
            raise ValueError(
                f"Stored composition {field_name} must be a JSON object."
            )

        return parsed

    @staticmethod
    def _serialize_datetime(value: datetime) -> str:
        return value.isoformat()

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        serialized = str(value)

        if serialized.endswith("Z"):
            serialized = f"{serialized[:-1]}+00:00"

        return datetime.fromisoformat(serialized)

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if not isinstance(value, str):
            return None

        normalized = value.strip()
        return normalized or None
