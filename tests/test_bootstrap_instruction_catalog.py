"""Bootstrap integration coverage for packaged instruction catalogs."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI

import src.app.bootstrap.application as bootstrap
from src.app.catalogs import load_instruction_catalog
from src.app.catalogs.instructions.loader import InstructionCatalog
from src.app.services.shared.settings import AppSettings
from src.app.services.execution_instructions import (
    ExecutionInstructionLibraryService,
)
from src.app.services.shared.instruction_catalog_synchronizer import (
    CatalogSynchronizationError,
    InstructionCatalogSynchronizer,
)


MIGRATIONS_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "sqlite"
)


def build_settings(database_path: Path) -> AppSettings:
    return cast(
        AppSettings,
        SimpleNamespace(
            database_path=database_path,
            encryption_key=Fernet.generate_key().decode("utf-8"),
            catalog_strict_versioning=False,
        ),
    )


async def apply_migrations_once(
    *,
    database_path: Path,
) -> None:
    if database_path.exists():
        return

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        for path in sorted(MIGRATIONS_PATH.glob("*.sql")):
            connection.executescript(
                path.read_text(encoding="utf-8")
            )


@pytest.mark.asyncio
async def test_bootstrap_orders_catalog_steps_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_path = tmp_path / "bootstrap.db"
    settings = build_settings(database_path)
    packaged_catalog = load_instruction_catalog()
    events: list[str] = []

    async def migrate(*, database_path: Path) -> None:
        events.append("migrations")
        await apply_migrations_once(
            database_path=database_path,
        )

    def load_catalog() -> InstructionCatalog:
        events.append("load")
        return packaged_catalog

    class RecordingSynchronizer(InstructionCatalogSynchronizer):
        def synchronize(self, catalog: InstructionCatalog):
            events.append("synchronize")
            return super().synchronize(catalog)

    async def ensure_tenant(**_: object) -> None:
        events.append("tenant")

    monkeypatch.setattr(
        bootstrap,
        "run_sqlite_migrations",
        migrate,
    )
    monkeypatch.setattr(
        bootstrap,
        "load_instruction_catalog",
        load_catalog,
    )
    monkeypatch.setattr(
        bootstrap,
        "InstructionCatalogSynchronizer",
        RecordingSynchronizer,
    )
    monkeypatch.setattr(
        bootstrap,
        "ensure_local_tenant",
        ensure_tenant,
    )

    first_app = FastAPI()

    with caplog.at_level(logging.INFO):
        await bootstrap.configure_application(
            first_app,
            settings=settings,
        )

    assert events == [
        "migrations",
        "load",
        "synchronize",
        "tenant",
    ]
    assert (
        first_app.state.catalog_synchronization.inserted
        == len(packaged_catalog.entries)
    )
    assert first_app.state.catalog_synchronization.unchanged == 0
    assert isinstance(
        first_app.state.execution_instruction_library_service,
        ExecutionInstructionLibraryService,
    )

    with sqlite3.connect(database_path) as connection:
        first_rows = connection.execute(
            """
            SELECT id, version, updated_at
            FROM instructions
            WHERE origin = 'builtin'
            ORDER BY id
            """
        ).fetchall()

    assert len(first_rows) == len(packaged_catalog.entries)
    assert "inserted=25 updated=0 unchanged=0 deprecated=0" in (
        caplog.text
    )

    events.clear()
    caplog.clear()
    second_app = FastAPI()

    with caplog.at_level(logging.INFO):
        await bootstrap.configure_application(
            second_app,
            settings=settings,
        )

    with sqlite3.connect(database_path) as connection:
        second_rows = connection.execute(
            """
            SELECT id, version, updated_at
            FROM instructions
            WHERE origin = 'builtin'
            ORDER BY id
            """
        ).fetchall()

    assert events == [
        "migrations",
        "load",
        "synchronize",
        "tenant",
    ]
    assert second_rows == first_rows
    assert second_app.state.catalog_synchronization.inserted == 0
    assert second_app.state.catalog_synchronization.updated == 0
    assert (
        second_app.state.catalog_synchronization.unchanged
        == len(packaged_catalog.entries)
    )
    assert "inserted=0 updated=0 unchanged=25 deprecated=0" in (
        caplog.text
    )


@pytest.mark.asyncio
async def test_bootstrap_accepts_an_injected_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "injected.db"
    packaged = load_instruction_catalog()
    injected = InstructionCatalog(
        skills=(packaged.skills[0],),
        personas=(),
    )

    async def ensure_tenant(**_: object) -> None:
        return None

    def must_not_load_packaged_catalog() -> InstructionCatalog:
        raise AssertionError(
            "Packaged catalog loader must not run when one is injected."
        )

    monkeypatch.setattr(
        bootstrap,
        "run_sqlite_migrations",
        apply_migrations_once,
    )
    monkeypatch.setattr(
        bootstrap,
        "ensure_local_tenant",
        ensure_tenant,
    )
    monkeypatch.setattr(
        bootstrap,
        "load_instruction_catalog",
        must_not_load_packaged_catalog,
    )
    app = FastAPI()

    await bootstrap.configure_application(
        app,
        settings=build_settings(database_path),
        instruction_catalog=injected,
    )

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id
            FROM instructions
            WHERE origin = 'builtin'
            """
        ).fetchall()

    assert rows == [(packaged.skills[0].id,)]
    assert app.state.instruction_catalog is injected


@pytest.mark.asyncio
async def test_synchronization_failure_stops_service_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "failed-sync.db"
    tenant_called = False

    class RejectingSynchronizer:
        def __init__(self, **_: object) -> None:
            pass

        def synchronize(
            self,
            catalog: InstructionCatalog,
        ) -> None:
            raise CatalogSynchronizationError(
                "Forced catalog synchronization failure."
            )

    async def ensure_tenant(**_: object) -> None:
        nonlocal tenant_called
        tenant_called = True

    monkeypatch.setattr(
        bootstrap,
        "run_sqlite_migrations",
        apply_migrations_once,
    )
    monkeypatch.setattr(
        bootstrap,
        "InstructionCatalogSynchronizer",
        RejectingSynchronizer,
    )
    monkeypatch.setattr(
        bootstrap,
        "ensure_local_tenant",
        ensure_tenant,
    )
    app = FastAPI()

    with pytest.raises(
        CatalogSynchronizationError,
        match="Forced catalog synchronization failure",
    ):
        await bootstrap.configure_application(
            app,
            settings=build_settings(database_path),
            instruction_catalog=load_instruction_catalog(),
        )

    assert tenant_called is False
    assert not hasattr(app.state, "persona_controller")
    assert not hasattr(app.state, "database")
