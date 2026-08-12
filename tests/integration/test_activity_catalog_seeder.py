"""Integration coverage for one-time workspace Activity catalog installation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest

from src.app.catalogs.loops import LOOP_CATALOG
from src.app.repositories.activities.sqlite_repository import (
    SqliteActivityRepository,
)
from src.app.schemas.activity import LoopActivityConfig
from src.app.services.activities.catalog_seeder import seed_activity_catalog
from tests.integration.conftest import WorkspaceFactory


@pytest.mark.asyncio
async def test_catalog_activities_are_installed_once_and_remain_user_owned(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Modified or deleted catalog activities must not be reset on later seeds."""

    await create_workspace(workspace_id='workspace-1')
    await create_workspace(workspace_id='workspace-2')
    identifiers = iter(f'id-{position}' for position in range(30))
    inserted = await seed_activity_catalog(
        database_path=sqlite_database_path,
        id_factory=lambda: next(identifiers),
        clock=lambda: datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
    )
    repository = SqliteActivityRepository(sqlite_database_path)
    workspace_one, total_one = await repository.list(
        workspace_id='workspace-1',
        offset=0,
        limit=10,
    )
    workspace_two, total_two = await repository.list(
        workspace_id='workspace-2',
        offset=0,
        limit=10,
    )

    assert inserted == 4
    assert total_one == total_two == 2
    assert {item.title for item in workspace_one} == {
        'shape ideas',
        'plan implementation',
    }
    assert {item.title for item in workspace_two} == {
        'shape ideas',
        'plan implementation',
    }
    assert all(
        item.type == 'loop' and item.status == 'active'
        for item in workspace_one
    )
    for activity in workspace_one:
        LoopActivityConfig.model_validate(activity.config)

    plan = next(
        item for item in workspace_one if item.title == 'plan implementation'
    )
    definition = next(
        entry
        for entry in LOOP_CATALOG
        if entry.id == 'builtin:loop:plan-implementation'
    )
    agents = plan.config['agents']
    assert isinstance(agents, list)
    assert plan.config == {
        'type': 'loop',
        'flow': definition.flow,
        'stop_conditions': {'max_iterations': definition.max_iterations},
        'agents': [
            {
                'id': agent['id'],
                'model_id': catalog_agent.model_id,
                'persona_id': catalog_agent.persona_id,
                'role': catalog_agent.role,
            }
            for agent, catalog_agent in zip(agents, definition.agents, strict=True)
        ],
        'output_contract': {
            'type': definition.output_type,
            'description': definition.output_description,
            'files': list(definition.output_files),
            'schema': definition.output_schema,
        },
    }
    assert all(isinstance(agent['id'], str) and agent['id'] for agent in agents)

    shape = next(
        item for item in workspace_one if item.title == 'shape ideas'
    )
    async with aiosqlite.connect(sqlite_database_path) as connection:
        await connection.execute('PRAGMA foreign_keys = ON')
        await connection.execute(
            'UPDATE activities SET title = ? WHERE id = ?',
            ('custom shape', shape.id),
        )
        await connection.execute(
            'DELETE FROM activities WHERE id = ?',
            (plan.id,),
        )
        await connection.commit()

    repeated = await seed_activity_catalog(database_path=sqlite_database_path)
    remaining, remaining_total = await repository.list(
        workspace_id='workspace-1',
        offset=0,
        limit=10,
    )

    assert repeated == 0
    assert remaining_total == 1
    assert remaining[0].title == 'custom shape'