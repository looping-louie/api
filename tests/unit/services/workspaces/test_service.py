"""Tests for workspace execution-default operations."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.models.workspace import ModelTarget, WorkspaceDefaults
from src.app.models.pipeline import PipelineHarness
from src.app.services.workspaces import WorkspaceService
from src.app.services.shared.tenant import TenantService, WorkspaceMembership
from tests.fakes.tenant_repository import FakeTenantRepository


class FakeWorkspaceRepository:
    """Store workspace defaults in memory for service tests."""

    def __init__(self) -> None:
        """Initialize an empty workspace-default store."""

        self.defaults_by_workspace_id: dict[str, WorkspaceDefaults] = {}

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


def build_service(
    *,
    repository: FakeWorkspaceRepository,
    linked_service_service: FakeLinkedServiceService,
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
        clock=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_returns_inherited_defaults_for_unconfigured_workspace() -> None:
    """An unconfigured workspace inherits both execution dimensions."""

    service = build_service(
        repository=FakeWorkspaceRepository(),
        linked_service_service=FakeLinkedServiceService(),
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
