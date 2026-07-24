"""SQLite row mapping and write helpers for loop persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import aiosqlite

from src.app.models.loop import (
    JsonObject,
    LoopAgent,
    LoopAgentRole,
    LoopChangelogEntry,
    LoopChangeType,
    LoopDocument,
    LoopFlow,
    LoopOutputContract,
    LoopOutputType,
    LoopStatus,
    LoopStopConditions,
)
from src.app.repositories.shared.json_mapping import (
    deserialize_json_object,
    serialize_json,
)


async def insert_loop(
    connection: aiosqlite.Connection,
    document: LoopDocument,
) -> None:
    """Insert the scalar portion of a loop aggregate."""

    await connection.execute(
        """
        INSERT INTO loops (
            id, workspace_id, title, description, flow, status,
            stop_conditions_json, output_contract_json, created_at,
            created_by, updated_at, updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document.id,
            document.workspace_id,
            document.title,
            document.description,
            document.flow,
            document.status,
            serialize_json(stop_conditions_dict(document)),
            serialize_json(output_contract_dict(document)),
            document.created_at.isoformat(),
            document.created_by,
            document.updated_at.isoformat(),
            document.updated_by,
        ),
    )


async def insert_agents(
    connection: aiosqlite.Connection,
    document: LoopDocument,
) -> None:
    """Insert all agents in their API order."""

    await connection.executemany(
        """
        INSERT INTO loop_agents (
            workspace_id, loop_id, position, id, model_id, persona_id, role
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                document.workspace_id,
                document.id,
                position,
                agent.id,
                agent.model_id,
                agent.persona_id,
                agent.role,
            )
            for position, agent in enumerate(document.agents)
        ],
    )


async def insert_changelog(
    connection: aiosqlite.Connection,
    entry: LoopChangelogEntry,
) -> None:
    """Append one immutable changelog entry."""

    await connection.execute(
        """
        INSERT INTO loop_changelog_entries (
            id, loop_id, workspace_id, change_type, actor_id,
            changed_at, diff_json, content_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.id,
            entry.loop_id,
            entry.workspace_id,
            entry.change_type,
            entry.actor_id,
            entry.changed_at.isoformat(),
            serialize_json(entry.diff),
            serialize_json(entry.content),
        ),
    )


async def to_document(
    connection: aiosqlite.Connection,
    row: aiosqlite.Row,
) -> LoopDocument:
    """Build a loop document from one loop row and its agents."""

    cursor = await connection.execute(
        """
        SELECT id, model_id, persona_id, role
        FROM loop_agents
        WHERE workspace_id = ? AND loop_id = ?
        ORDER BY position ASC
        """,
        (row["workspace_id"], row["id"]),
    )
    try:
        agent_rows = await cursor.fetchall()
    finally:
        await cursor.close()

    stop = cast(
        JsonObject,
        deserialize_json_object(row["stop_conditions_json"]),
    )
    output = cast(
        JsonObject,
        deserialize_json_object(row["output_contract_json"]),
    )
    return LoopDocument(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        title=str(row["title"]),
        description=str(row["description"]),
        flow=cast(LoopFlow, row["flow"]),
        status=cast(LoopStatus, row["status"]),
        stop_conditions=LoopStopConditions(**stop),
        agents=tuple(
            LoopAgent(
                id=str(agent["id"]),
                model_id=str(agent["model_id"]),
                persona_id=str(agent["persona_id"]),
                role=cast(LoopAgentRole, agent["role"]),
            )
            for agent in agent_rows
        ),
        output_contract=LoopOutputContract(
            type=cast(LoopOutputType, output["type"]),
            description=str(output["description"]),
            files=tuple(output["files"]),
            schema=cast(JsonObject | None, output["schema"]),
        ),
        created_at=datetime.fromisoformat(row["created_at"]),
        created_by=str(row["created_by"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        updated_by=str(row["updated_by"]),
    )


def to_changelog_entry(row: aiosqlite.Row) -> LoopChangelogEntry:
    """Build one changelog entry from a database row."""

    return LoopChangelogEntry(
        id=str(row["id"]),
        loop_id=str(row["loop_id"]),
        workspace_id=str(row["workspace_id"]),
        change_type=cast(LoopChangeType, row["change_type"]),
        actor_id=str(row["actor_id"]),
        changed_at=datetime.fromisoformat(row["changed_at"]),
        diff=deserialize_json_object(row["diff_json"]),
        content=deserialize_json_object(row["content_json"]),
    )


def loop_update_values(document: LoopDocument) -> tuple[Any, ...]:
    """Return SQL parameters for replacing mutable loop fields."""

    return (
        document.title,
        document.description,
        document.flow,
        document.status,
        serialize_json(stop_conditions_dict(document)),
        serialize_json(output_contract_dict(document)),
        document.updated_at.isoformat(),
        document.updated_by,
        document.workspace_id,
        document.id,
    )


def stop_conditions_dict(document: LoopDocument) -> JsonObject:
    """Serialize stop conditions without dropping absent fields."""

    stop = document.stop_conditions
    return {
        "max_iterations": stop.max_iterations,
        "max_tokens": stop.max_tokens,
        "timeout_seconds": stop.timeout_seconds,
    }


def output_contract_dict(document: LoopDocument) -> JsonObject:
    """Serialize an output contract to JSON-compatible values."""

    output = document.output_contract
    return {
        "type": output.type,
        "description": output.description,
        "files": list(output.files),
        "schema": output.schema,
    }
