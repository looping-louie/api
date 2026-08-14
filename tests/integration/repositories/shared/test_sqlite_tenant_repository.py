"""Integration tests for SqliteTenantRepository."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from src.app.repositories.shared.tenant_repository import (
    SqliteTenantRepository,
)


WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest.mark.asyncio
async def test_get_membership_returns_matching_membership(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
        memberships=(
            (
                "user-1",
                "owner",
                True,
            ),
        ),
    )
    repository = SqliteTenantRepository(
        sqlite_database_path,
    )

    membership = await repository.get_membership(
        user_id="user-1",
        workspace_id="workspace-1",
    )

    assert membership is not None
    assert membership.user_id == "user-1"
    assert membership.workspace_id == "workspace-1"
    assert membership.is_default is True


@pytest.mark.asyncio
async def test_get_membership_isolated_by_user(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
        memberships=(
            (
                "user-1",
                "owner",
                True,
            ),
        ),
    )
    repository = SqliteTenantRepository(
        sqlite_database_path,
    )

    membership = await repository.get_membership(
        user_id="user-2",
        workspace_id="workspace-1",
    )

    assert membership is None


@pytest.mark.asyncio
async def test_get_default_membership_returns_default_workspace(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-secondary",
        memberships=(
            (
                "user-1",
                "member",
                False,
            ),
        ),
    )
    await create_workspace(
        workspace_id="workspace-default",
        memberships=(
            (
                "user-1",
                "owner",
                True,
            ),
        ),
    )
    repository = SqliteTenantRepository(
        sqlite_database_path,
    )

    membership = await repository.get_default_membership(
        user_id="user-1",
    )

    assert membership is not None
    assert membership.workspace_id == "workspace-default"
    assert membership.is_default is True


@pytest.mark.asyncio
async def test_get_default_membership_returns_none_without_default(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
        memberships=(
            (
                "user-1",
                "member",
                False,
            ),
        ),
    )
    repository = SqliteTenantRepository(
        sqlite_database_path,
    )

    membership = await repository.get_default_membership(
        user_id="user-1",
    )

    assert membership is None


@pytest.mark.asyncio
async def test_list_memberships_returns_default_first(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-secondary",
        memberships=(
            (
                "user-1",
                "member",
                False,
            ),
        ),
    )
    await create_workspace(
        workspace_id="workspace-default",
        memberships=(
            (
                "user-1",
                "owner",
                True,
            ),
        ),
    )
    await create_workspace(
        workspace_id="workspace-other-user",
        memberships=(
            (
                "user-2",
                "owner",
                True,
            ),
        ),
    )
    repository = SqliteTenantRepository(
        sqlite_database_path,
    )

    memberships = await repository.list_memberships(
        user_id="user-1",
    )

    assert [
        membership.workspace_id
        for membership in memberships
    ] == [
        "workspace-default",
        "workspace-secondary",
    ]
    assert all(
        membership.user_id == "user-1"
        for membership in memberships
    )


@pytest.mark.asyncio
async def test_list_memberships_returns_empty_for_unknown_user(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
        memberships=(
            (
                "user-1",
                "owner",
                True,
            ),
        ),
    )
    repository = SqliteTenantRepository(
        sqlite_database_path,
    )

    memberships = await repository.list_memberships(
        user_id="missing-user",
    )

    assert memberships == []
