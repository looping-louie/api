import pytest

from src.app.services.shared.tenant import (
    TenantAccessDeniedError,
    TenantNotFoundError,
    TenantSelectionRequiredError,
    TenantService,
    WorkspaceMembership,
)
from tests.fakes.tenant_repository import FakeTenantRepository


@pytest.mark.asyncio
async def test_resolve_requested_workspace() -> None:
    repository = FakeTenantRepository(
        [
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-1",
            ),
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-2",
            ),
        ]
    )
    service = TenantService(repository=repository)

    context = await service.resolve(
        user_id="user-1",
        requested_workspace_id="workspace-2",
    )

    assert context.user_id == "user-1"
    assert context.workspace_id == "workspace-2"


@pytest.mark.asyncio
async def test_resolve_default_workspace() -> None:
    repository = FakeTenantRepository(
        [
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-1",
            ),
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-2",
                is_default=True,
            ),
        ]
    )
    service = TenantService(repository=repository)

    context = await service.resolve(user_id="user-1")

    assert context.workspace_id == "workspace-2"


@pytest.mark.asyncio
async def test_resolve_only_enabled_workspace() -> None:
    repository = FakeTenantRepository(
        [
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-disabled",
                is_enabled=False,
            ),
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-enabled",
            ),
        ]
    )
    service = TenantService(repository=repository)

    context = await service.resolve(user_id="user-1")

    assert context.workspace_id == "workspace-enabled"


@pytest.mark.asyncio
async def test_resolve_requires_selection_for_multiple_workspaces() -> None:
    repository = FakeTenantRepository(
        [
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-1",
            ),
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-2",
            ),
        ]
    )
    service = TenantService(repository=repository)

    with pytest.raises(TenantSelectionRequiredError) as error:
        await service.resolve(user_id="user-1")

    assert error.value.workspace_ids == (
        "workspace-1",
        "workspace-2",
    )


@pytest.mark.asyncio
async def test_resolve_rejects_inaccessible_workspace() -> None:
    repository = FakeTenantRepository(
        [
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-1",
            ),
        ]
    )
    service = TenantService(repository=repository)

    with pytest.raises(TenantAccessDeniedError):
        await service.resolve(
            user_id="user-1",
            requested_workspace_id="workspace-2",
        )


@pytest.mark.asyncio
async def test_resolve_rejects_user_without_workspace() -> None:
    service = TenantService(repository=FakeTenantRepository())

    with pytest.raises(TenantNotFoundError):
        await service.resolve(user_id="user-1")
