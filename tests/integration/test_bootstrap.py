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
from src.app.controllers.activity import ActivityController
from src.app.controllers.activity_run import ActivityRunController
from src.app.controllers.persona import PersonaController
from src.app.controllers.pipeline import PipelineController
from src.app.controllers.skill import SkillController
from src.app.controllers.workspace import WorkspaceController
from src.app.controllers.user import UserModelController
from src.app.controllers.user import UserController
from src.app.repositories.infrastructure.sqlite_database import (
    SqliteDatabase,
)
from src.app.services.shared.settings import AppSettings


EXPECTED_TABLES = {
    "schema_migrations",
    "workspaces",
    "workspace_memberships",
    "instructions",
    "pipelines",
    "pipeline_steps",
    "pipeline_step_dependencies",
    "pipeline_changelog_entries",
    "linked_services",
    "persona_skills",
    "workspace_instruction_settings",
    "user_skill_settings",
    "user_persona_settings",
    "activities",
    "activity_catalog_installations",
    "activity_changelog_entries",
    "activity_runs",
    "activity_run_checkpoints",
    "activity_run_idempotency",
    "pipeline_runs",
    "pipeline_run_steps",
    "pipeline_run_events",
    "workers",
    "users",
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
            app.state.activity_controller,
            ActivityController,
        )
        assert isinstance(
            app.state.activity_run_controller,
            ActivityRunController,
        )
        assert isinstance(
            app.state.pipeline_controller,
            PipelineController,
        )
        assert isinstance(
            app.state.user_model_controller,
            UserModelController,
        )
        assert isinstance(
            app.state.workspace_controller,
            WorkspaceController,
        )
        assert isinstance(
            app.state.user_controller,
            UserController,
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
        activity_rows = connection.execute(
            """
            SELECT name
            FROM activities
            WHERE workspace_id = 'local-workspace'
            ORDER BY name
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
    assert not {
        'loops',
        'loop_agents',
        'loop_catalog_installations',
        'loop_changelog_entries',
        'loop_runs',
        'loop_run_checkpoints',
        'loop_run_idempotency',
    } & table_names
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
        "0011_loop_run_checkpoints",
        "0012_expand_loop_run_states",
        "0013_repair_loop_run_idempotency",
        "0014_activities",
        "0015_pipeline_activity_steps",
        "0016_activity_loop_runs",
        "0017_activity_catalog_installations",
        "0018_archive_builtin_activities",
            "0019_flatten_approval_activities",
        "0020_flatten_quiz_activities",
        "0021_flatten_direct_loop_activities",
        "0022_flatten_refinement_loop_activities",
        "0023_flatten_roundtable_loop_activities",
        "0024_remove_activity_config_type",
        "0025_rename_activity_pipeline_titles",
        "0026_persona_models",
        "0027_pipeline_step_dependencies",
        "0028_rename_pipeline_dependency_success_condition",
        "0029_activity_runs",
        "0030_pipeline_runs",
        "0031_linked_services",
        "0032_persona_linked_service_selections",
        "0033_pipeline_run_worker_claims",
        "0034_pipeline_run_commit_mode",
        "0035_remove_legacy_loops",
        "0036_pipeline_run_events_and_gates",
        "0037_unify_human_activity_runs",
        "0038_prepared_pipeline_runs",
        "0039_workers",
        "0040_retire_legacy_provider_credentials",
            "0041_pipeline_harness",
            "0042_worker_harnesses",
            "0043_workspace_execution_defaults",
            "0044_execution_overrides",
                "0045_remove_persona_linked_service_selections",
            "0046_users",
            "0047_user_owned_instructions",
            "0048_user_skill_settings",
                "0049_user_persona_settings",
                "0050_user_owned_linked_services",
                "0051_user_execution_settings",
                    "0052_logical_model_overrides",
                        "0053_user_owned_activities",
                        "0054_user_owned_pipelines",
                        "0055_user_execution_defaults",
    ]
    assert activity_rows == []


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
