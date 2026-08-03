"""Integration tests for the application composition root."""

from __future__ import annotations

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.bootstrap import configure_application
from src.app.controllers.loop import LoopController
from src.app.controllers.loop_run import LoopRunController
from src.app.controllers.model import ModelController
from src.app.controllers.persona import PersonaController
from src.app.controllers.pipeline import PipelineController
from src.app.controllers.provider import ProviderController
from src.app.controllers.skill import SkillController
from src.app.repositories.infrastructure.sqlite_database import (
    SqliteDatabase,
)
from src.app.services.shared.settings import AppSettings


EXPECTED_TABLES = {
    "schema_migrations",
    "workspaces",
    "workspace_memberships",
    "instructions",
    "loops",
    "loop_agents",
    "loop_catalog_installations",
    "loop_changelog_entries",
    "loop_runs",
    "pipelines",
    "pipeline_steps",
    "pipeline_changelog_entries",
    "provider_credentials",
    "persona_skills",
    "workspace_instruction_settings",
}


def build_settings(
    *,
    database_path: Path,
    encryption_key: str | None = None,
) -> AppSettings:
    """Build the minimum settings required by bootstrap."""

    return cast(
        AppSettings,
        SimpleNamespace(
            database_path=database_path,
            encryption_key=(
                encryption_key
                or Fernet.generate_key().decode("utf-8")
            ),
        ),
    )


def test_bootstrap_configures_application_and_runs_migrations(
    tmp_path: Path,
) -> None:
    """Startup should wire controllers and prepare the SQLite database."""

    database_path = tmp_path / "looping-louie-bootstrap.db"
    settings = build_settings(
        database_path=database_path,
    )

    @asynccontextmanager
    async def lifespan(
        app: FastAPI,
    ) -> AsyncIterator[None]:
        """Configure the application for the duration of this test."""

        await configure_application(
            app,
            settings=settings,
        )
        yield

    app = FastAPI(
        lifespan=lifespan,
    )

    assert database_path.exists() is False

    with TestClient(app):
        assert isinstance(
            app.state.persona_controller,
            PersonaController,
        )
        assert isinstance(
            app.state.skill_controller,
            SkillController,
        )
        assert isinstance(
            app.state.loop_controller,
            LoopController,
        )
        assert isinstance(
            app.state.loop_run_controller,
            LoopRunController,
        )
        assert isinstance(
            app.state.pipeline_controller,
            PipelineController,
        )
        assert isinstance(
            app.state.model_controller,
            ModelController,
        )
        assert isinstance(
            app.state.provider_controller,
            ProviderController,
        )
        assert isinstance(
            app.state.database,
            SqliteDatabase,
        )

    assert database_path.exists() is True

    with sqlite3.connect(database_path) as connection:
        table_rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

        migration_rows = connection.execute(
            """
            SELECT version
            FROM schema_migrations
            ORDER BY version ASC
            """
        ).fetchall()
        loop_rows = connection.execute(
            """
            SELECT title
            FROM loops
            WHERE workspace_id = 'local-workspace'
            ORDER BY title
            """
        ).fetchall()

    table_names = {
        str(row[0])
        for row in table_rows
    }
    migration_versions = [
        str(row[0])
        for row in migration_rows
    ]

    assert EXPECTED_TABLES <= table_names
    assert migration_versions == [
        "0001_tenants",
        "0002_instructions",
        "0004_provider_credentials",
        "0005_instruction_catalog",
        "0006_loops",
        "0007_persona_skills",
        "0008_loop_catalog_installations",
        "0009_pipelines",
        "0010_loop_runs",
    ]
    assert [str(row[0]) for row in loop_rows] == [
        "plan implementation",
        "shape ideas",
    ]


@pytest.mark.asyncio
async def test_bootstrap_requires_provider_encryption_key(
    tmp_path: Path,
) -> None:
    """Startup should fail securely without an encryption key."""

    app = FastAPI()
    settings = build_settings(
        database_path=tmp_path / "missing-key.db",
        encryption_key="temporary",
    )
    settings = cast(
        AppSettings,
        SimpleNamespace(
            database_path=settings.database_path,
            encryption_key=None,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="LOUIE_ENCRYPTION_KEY is required",
    ):
        await configure_application(
            app,
            settings=settings,
        )
