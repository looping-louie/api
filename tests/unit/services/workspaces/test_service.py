"""Tests for workspace execution-default operations."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.models.execution import ModelTarget
from src.app.models.user import UserDocument
from src.app.models.workspace import WorkspaceDefaults, WorkspaceDocument
from src.app.models.pipeline import PipelineHarness
from src.app.services.workspaces import WorkspaceService
from src.app.services.shared.tenant import TenantService, WorkspaceMembership
from tests.fakes.tenant_repository import FakeTenantRepository


class FakeWorkspaceRepository:
    """Store workspace defaults in memory for service tests."""

    def __init__(self) -> None:
        """Initialize an empty workspace-default store."""

        self.defaults_by_workspace_id: dict[str, WorkspaceDefaults] = {}
        self.workspaces_by_user_id: dict[str, list[WorkspaceDocument]] = {}

    async def create(
        self,
        *,
        workspace: WorkspaceDocument,
        owner_id: str,
    ) -> WorkspaceDocument:
        """Store a Workspace in its owner's collection."""

        self.workspaces_by_user_id.setdefault(owner_id, []).append(workspace)
        return workspace

    async def list_for_user(self, *, user_id: str) -> list[WorkspaceDocument]:
        """Return Workspaces stored for one User."""

        return list(self.workspaces_by_user_id.get(user_id, []))

    async def get(
        self,
        *,
        workspace_id: str,
    ) -> WorkspaceDefaults | None:
        """Return defaults stored for one workspace."""

        return self.defaults_by_workspace_id.get(workspace_id)

    async def replace(
        self,
        *,
        defaults: WorkspaceDefaults,
    ) -> WorkspaceDefaults:
        """Replace the stored defaults for one workspace."""

        self.defaults_by_workspace_id[defaults.workspace_id] = defaults
        return defaults


class FakeLinkedServiceService:
    """Capture model-target validation requests."""

    def __init__(self) -> None:
        """Initialize an empty validation-call log."""

        self.calls: list[tuple[str, str, str]] = []

    async def require_available_selection(
        self,
        *,
        workspace_id: str,
        service_id: str,
        model_id: str,
    ) -> None:
        """Record the selection requested for validation."""

        self.calls.append((workspace_id, service_id, model_id))


class FakeUserService:
    """Record profile lookups required before workspace operations."""

    def __init__(self) -> None:
        """Initialize the User lookup log."""

        self.user_ids: list[str] = []

    async def get(self, *, user_id: str) -> UserDocument:
        """Return a durable profile for the requested User."""

        self.user_ids.append(user_id)
        timestamp = datetime(2026, 8, 25, tzinfo=timezone.utc)
        return UserDocument(
            id=user_id,
            created_at=timestamp,
            updated_at=timestamp,
        )


def build_service(
    *,
    repository: FakeWorkspaceRepository,
    linked_service_service: FakeLinkedServiceService,
    user_service: FakeUserService,
) -> WorkspaceService:
    """Build the service for one default workspace membership."""

    tenant_service = TenantService(
        repository=FakeTenantRepository(
            [
                WorkspaceMembership(
                    user_id='user-1',
                    workspace_id='workspace-1',
                    is_default=True,
                ),
            ],
        ),
    )
    return WorkspaceService(
        repository=repository,
        tenant_service=tenant_service,
        linked_service_service=linked_service_service,  # type: ignore[arg-type]
        user_service=user_service,  # type: ignore[arg-type]
        id_factory=lambda: 'workspace-created',
        clock=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_returns_inherited_defaults_for_unconfigured_workspace() -> None:
    """An unconfigured workspace inherits both execution dimensions."""

    service = build_service(
        repository=FakeWorkspaceRepository(),
        linked_service_service=FakeLinkedServiceService(),
        user_service=FakeUserService(),
    )

    defaults = await service.get_defaults(user_id='user-1')

    assert defaults.workspace_id == 'workspace-1'
    assert defaults.model_target is None
    assert defaults.harness is None


@pytest.mark.asyncio
async def test_replace_validates_and_persists_model_target_and_harness() -> None:
    """Workspace overrides validate their route and preserve both dimensions."""

    repository = FakeWorkspaceRepository()
    linked_service_service = FakeLinkedServiceService()
    service = build_service(
        repository=repository,
        linked_service_service=linked_service_service,
        user_service=FakeUserService(),
    )

    defaults = await service.replace_defaults(
        user_id='user-1',
        model_target=ModelTarget(
            linked_service_id='service-primary',
            model_id='gpt-5',
        ),
        harness=PipelineHarness(kind='codex_cli'),
    )

    assert linked_service_service.calls == [
        ('workspace-1', 'service-primary', 'gpt-5'),
    ]
    assert defaults == repository.defaults_by_workspace_id['workspace-1']
    assert defaults.model_target == ModelTarget(
        linked_service_id='service-primary',
        model_id='gpt-5',
    )
    assert defaults.harness == PipelineHarness(kind='codex_cli')


@pytest.mark.asyncio
async def test_create_assigns_workspace_to_the_requesting_user() -> None:
    """Workspace creation verifies the User and stores its owned workspace."""

    repository = FakeWorkspaceRepository()
    user_service = FakeUserService()
    service = build_service(
        repository=repository,
        linked_service_service=FakeLinkedServiceService(),
        user_service=user_service,
    )

    workspace = await service.create(user_id='user-1', name='Acme')

    assert user_service.user_ids == ['user-1']
    assert workspace.id == 'workspace-created'
    assert repository.workspaces_by_user_id['user-1'] == [workspace]


@pytest.mark.asyncio
async def test_list_for_user_returns_only_its_workspaces() -> None:
    """Workspace listings are scoped to the requesting User."""

    repository = FakeWorkspaceRepository()
    user_service = FakeUserService()
    service = build_service(
        repository=repository,
        linked_service_service=FakeLinkedServiceService(),
        user_service=user_service,
    )
    await service.create(user_id='user-1', name='Acme')
    repository.workspaces_by_user_id['user-2'] = [
        WorkspaceDocument(
            id='workspace-other',
            name='Other',
            created_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            updated_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ),
    ]

    workspaces = await service.list_for_user(user_id='user-1')

    assert user_service.user_ids == ['user-1', 'user-1']
    assert [workspace.id for workspace in workspaces] == ['workspace-created']
