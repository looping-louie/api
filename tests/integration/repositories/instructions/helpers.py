"""SQL helpers shared by instruction availability tests."""

import sqlite3


TIMESTAMP = "2026-07-23T12:00:00+00:00"


def insert_custom(
    connection: sqlite3.Connection,
    *,
    instruction_id: str,
    project_id: str,
    name: str,
    description: str,
) -> None:
    """Insert one custom skill directly for query behavior tests."""

    connection.execute(
        """
        INSERT INTO instructions (
            id, instruction_type, origin, owner_project_id, name, name_key,
            description, content, metadata_json, enabled_by_default,
            deprecated, version, created_at, updated_at
        )
        VALUES (?, 'skill', 'custom', ?, ?, ?, ?, ?, '{}', 1, 0, 1, ?, ?)
        """,
        (
            instruction_id,
            project_id,
            name,
            normalize(name),
            description,
            f"Instructions for {name}.",
            TIMESTAMP,
            TIMESTAMP,
        ),
    )


def insert_marketplace(connection: sqlite3.Connection) -> None:
    """Insert one marketplace skill directly for visibility tests."""

    connection.execute(
        """
        INSERT INTO instructions (
            id, instruction_type, origin, owner_project_id, name, name_key,
            description, content, metadata_json, catalog_version, checksum,
            enabled_by_default, deprecated, version, created_at, updated_at
        )
        VALUES (
            'marketplace-skill', 'skill', 'marketplace', NULL,
            'Marketplace Skill', 'marketplace skill',
            'Authorized marketplace content.', 'Marketplace instructions.',
            '{}', 1, ?, 0, 0, 1, ?, ?
        )
        """,
        ("f" * 64, TIMESTAMP, TIMESTAMP),
    )


def normalize(value: str) -> str:
    """Normalize display text using repository name semantics."""

    return " ".join(value.strip().casefold().split())
