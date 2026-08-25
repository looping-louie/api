"""Transactional materialization of builtin Persona and Skill catalogs."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from src.app.catalogs.persona_skills import (
    CatalogInstructionEntry,
    InstructionOrigin,
    PersonaCatalogEntry,
)
from src.app.catalogs.persona_skills.loader import PersonaSkillCatalog
from .serialization import (
    serialize_catalog_metadata,
)


Clock = Callable[[], datetime]
LOGGER = logging.getLogger(__name__)


class CatalogChecksumPolicy(StrEnum):
    """Policy for content changes without a catalog version increment."""

    ALLOW_WITH_WARNING = "allow_with_warning"
    REQUIRE_VERSION_INCREMENT = "require_version_increment"


class CatalogSynchronizationError(RuntimeError):
    """Base error raised while materializing the Persona and Skill catalog."""


class CatalogVersionRegressionError(CatalogSynchronizationError):
    """Raised when packaged catalog content reduces a stored version."""


class CatalogChecksumConflictError(CatalogSynchronizationError):
    """Raised for an unversioned content change under strict policy."""


class CatalogIdentityConflictError(CatalogSynchronizationError):
    """Raised when a builtin ID is already owned by another origin."""


@dataclass(frozen=True, slots=True)
class CatalogSynchronizationResult:
    """Summary of one committed synchronization."""

    inserted: int
    updated: int
    deprecated: int
    unchanged: int


@dataclass(frozen=True, slots=True)
class _StoredInstruction:
    id: str
    origin: str
    catalog_version: int | None
    checksum: str | None
    deprecated: bool


class PersonaSkillCatalogSynchronizer:
    """Synchronize immutable builtin definitions into SQLite."""

    def __init__(
        self,
        *,
        database_path: str | Path,
        checksum_policy: CatalogChecksumPolicy = (
            CatalogChecksumPolicy.ALLOW_WITH_WARNING
        ),
        clock: Clock | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._database_path = Path(database_path)
        self._checksum_policy = checksum_policy
        self._clock = clock or self._utc_now
        self._logger = logger or LOGGER

    def synchronize(
        self,
        catalog: PersonaSkillCatalog,
    ) -> CatalogSynchronizationResult:
        """Materialize one validated catalog in a single transaction."""

        entries = catalog.entries
        self._validate_catalog_entries(entries)
        timestamp = self._clock().isoformat()
        warnings: list[str] = []

        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            connection.execute("BEGIN IMMEDIATE")
            stored = self._load_stored_instructions(connection)
            inserts: list[CatalogInstructionEntry] = []
            updates: list[CatalogInstructionEntry] = []
            unchanged = 0

            for entry in entries:
                current = stored.get(entry.id)

                if current is None:
                    inserts.append(entry)
                    continue

                if current.origin != InstructionOrigin.BUILTIN:
                    raise CatalogIdentityConflictError(
                        f"Catalog id '{entry.id}' is already owned by "
                        f"origin '{current.origin}'."
                    )

                self._validate_version_transition(
                    entry=entry,
                    stored=current,
                    warnings=warnings,
                )

                if self._requires_update(entry, current):
                    updates.append(entry)
                else:
                    unchanged += 1

            incoming_ids = {
                entry.id
                for entry in entries
            }
            retired_ids = [
                current.id
                for current in stored.values()
                if (
                    current.origin == InstructionOrigin.BUILTIN
                    and current.id not in incoming_ids
                    and not current.deprecated
                )
            ]

            for entry in inserts:
                self._insert_entry(
                    connection,
                    entry=entry,
                    timestamp=timestamp,
                )

            for entry in updates:
                self._update_entry(
                    connection,
                    entry=entry,
                    timestamp=timestamp,
                )

            if retired_ids:
                connection.executemany(
                    """
                    UPDATE instructions
                    SET
                        deprecated = 1,
                        version = version + 1,
                        updated_at = ?
                    WHERE id = ?
                      AND origin = 'builtin'
                      AND deprecated = 0
                    """,
                    [
                        (
                            timestamp,
                            instruction_id,
                        )
                        for instruction_id in retired_ids
                    ],
                )

            for entry in entries:
                if isinstance(entry, PersonaCatalogEntry):
                    self._replace_persona_skills(
                        connection,
                        persona_id=entry.id,
                        skill_ids=entry.skill_ids,
                    )

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        for warning in warnings:
            self._logger.warning(warning)

        return CatalogSynchronizationResult(
            inserted=len(inserts),
            updated=len(updates),
            deprecated=len(retired_ids),
            unchanged=unchanged,
        )

    def _validate_version_transition(
        self,
        *,
        entry: CatalogInstructionEntry,
        stored: _StoredInstruction,
        warnings: list[str],
    ) -> None:
        catalog_version = self._require_catalog_version(entry)
        stored_version = stored.catalog_version

        if stored_version is None:
            raise CatalogSynchronizationError(
                f"Stored builtin '{entry.id}' has no catalog_version."
            )

        if catalog_version < stored_version:
            raise CatalogVersionRegressionError(
                f"Catalog version for '{entry.id}' cannot decrease "
                f"from {stored_version} to {catalog_version}."
            )

        checksum = self._require_checksum(entry)

        if (
            catalog_version != stored_version
            or checksum == stored.checksum
        ):
            return

        message = (
            f"Builtin '{entry.id}' changed checksum without incrementing "
            f"catalog_version {catalog_version}."
        )

        if (
            self._checksum_policy
            == CatalogChecksumPolicy.REQUIRE_VERSION_INCREMENT
        ):
            raise CatalogChecksumConflictError(message)

        warnings.append(
            f"{message} Accepting the change under development policy."
        )

    @staticmethod
    def _requires_update(
        entry: CatalogInstructionEntry,
        stored: _StoredInstruction,
    ) -> bool:
        return (
            entry.catalog_version != stored.catalog_version
            or entry.checksum != stored.checksum
            or entry.deprecated != stored.deprecated
        )

    @staticmethod
    def _load_stored_instructions(
        connection: sqlite3.Connection,
    ) -> dict[str, _StoredInstruction]:
        rows = connection.execute(
            """
            SELECT
                id,
                origin,
                catalog_version,
                checksum,
                deprecated
            FROM instructions
            """
        ).fetchall()

        return {
            str(row["id"]): _StoredInstruction(
                id=str(row["id"]),
                origin=str(row["origin"]),
                catalog_version=(
                    int(row["catalog_version"])
                    if row["catalog_version"] is not None
                    else None
                ),
                checksum=(
                    str(row["checksum"])
                    if row["checksum"] is not None
                    else None
                ),
                deprecated=bool(row["deprecated"]),
            )
            for row in rows
        }

    @classmethod
    def _insert_entry(
        cls,
        connection: sqlite3.Connection,
        *,
        entry: CatalogInstructionEntry,
        timestamp: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO instructions (
                id,
                instruction_type,
                origin,
                owner_workspace_id,
                source_instruction_id,
                name,
                name_key,
                description,
                content,
                metadata_json,
                catalog_version,
                checksum,
                enabled_by_default,
                deprecated,
                version,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, 'builtin', NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                1, ?, ?
            )
            """,
            cls._entry_values(entry, timestamp=timestamp),
        )

    @classmethod
    def _update_entry(
        cls,
        connection: sqlite3.Connection,
        *,
        entry: CatalogInstructionEntry,
        timestamp: str,
    ) -> None:
        values = cls._entry_values(
            entry,
            timestamp=timestamp,
        )
        connection.execute(
            """
            UPDATE instructions
            SET
                instruction_type = ?,
                origin = 'builtin',
                owner_workspace_id = NULL,
                source_instruction_id = NULL,
                name = ?,
                name_key = ?,
                description = ?,
                content = ?,
                metadata_json = ?,
                catalog_version = ?,
                checksum = ?,
                enabled_by_default = ?,
                deprecated = ?,
                version = version + 1,
                updated_at = ?
            WHERE id = ?
              AND origin = 'builtin'
            """,
            (
                *values[1:11],
                values[-1],
                values[0],
            ),
        )

    @classmethod
    def _entry_values(
        cls,
        entry: CatalogInstructionEntry,
        *,
        timestamp: str,
    ) -> tuple[object, ...]:
        return (
            entry.id,
            entry.instruction_type.value,
            entry.name,
            cls._normalize_name(entry.name),
            entry.description,
            entry.instructions,
            serialize_catalog_metadata(entry),
            cls._require_catalog_version(entry),
            cls._require_checksum(entry),
            int(entry.enabled_by_default),
            int(entry.deprecated),
            timestamp,
            timestamp,
        )

    @staticmethod
    def _replace_persona_skills(
        connection: sqlite3.Connection,
        *,
        persona_id: str,
        skill_ids: tuple[str, ...],
    ) -> None:
        """Synchronize one builtin persona's ordered skill associations."""

        connection.execute(
            "DELETE FROM persona_skills WHERE persona_id = ?",
            (persona_id,),
        )
        connection.executemany(
            """
            INSERT INTO persona_skills (
                persona_id,
                skill_id,
                position
            )
            VALUES (?, ?, ?)
            """,
            [
                (persona_id, skill_id, position)
                for position, skill_id in enumerate(skill_ids)
            ],
        )

    @staticmethod
    def _validate_catalog_entries(
        entries: tuple[CatalogInstructionEntry, ...],
    ) -> None:
        seen_ids: set[str] = set()

        for entry in entries:
            if entry.origin != InstructionOrigin.BUILTIN:
                raise CatalogSynchronizationError(
                    f"Instruction catalog synchronizer only accepts "
                    f"builtins; '{entry.id}' has origin "
                    f"'{entry.origin.value}'."
                )

            if entry.id in seen_ids:
                raise CatalogSynchronizationError(
                    f"Duplicate builtin catalog id: {entry.id}"
                )

            seen_ids.add(entry.id)
            PersonaSkillCatalogSynchronizer._require_catalog_version(
                entry
            )
            PersonaSkillCatalogSynchronizer._require_checksum(entry)

    @staticmethod
    def _require_catalog_version(
        entry: CatalogInstructionEntry,
    ) -> int:
        version = entry.catalog_version

        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version < 1
        ):
            raise CatalogSynchronizationError(
                f"Builtin '{entry.id}' requires a positive "
                "catalog_version."
            )

        return version

    @staticmethod
    def _require_checksum(
        entry: CatalogInstructionEntry,
    ) -> str:
        checksum = entry.checksum

        if checksum is None:
            raise CatalogSynchronizationError(
                f"Builtin '{entry.id}' requires a checksum."
            )

        return checksum

    @staticmethod
    def _normalize_name(name: str) -> str:
        return " ".join(
            name.strip().casefold().split()
        )

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)
