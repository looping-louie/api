"""Application service for workspace execution defaults."""
    )

from collections.abc import Callable
from datetime import datetime

from src.app.models.execution import ModelTarget
from src.app.models.workspace import WorkspaceDefaults
from src.app.models.workspace import WorkspaceDocument
from src.app.models.pipeline import PipelineHarness
from src.app.repositories.workspaces import WorkspaceRepository
from src.app.services.linked_services import LinkedServiceService
from src.app.services.shared.tenant import TenantService
from src.app.services.users import UserService


class WorkspaceService:
    """Read and replace optional defaults for one workspace."""

    def __init__(
        self,
        *,
        repository: WorkspaceRepository,
        tenant_service: TenantService,
        linked_service_service: LinkedServiceService,
        user_service: UserService,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        """Store workspace resolution, validation, persistence, and clock."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._linked_service_service = linked_service_service
        self._user_service = user_service
        self._id_factory = id_factory
        self._clock = clock

    async def create(
        self,
        *,
        user_id: str,
        name: str,
    ) -> WorkspaceDocument:
        """Create a workspace owned by an existing user."""

        await self._user_service.get(user_id=user_id)
        now = self._clock()
        return await self._repository.create(
            workspace=WorkspaceDocument(
                id=self._id_factory(),
                name=name,
                created_at=now,
                updated_at=now,
            ),
            owner_id=user_id,
        )

    async def list_for_user(self, *, user_id: str) -> list[WorkspaceDocument]:
        """Return workspaces accessible to an existing user."""

        await self._user_service.get(user_id=user_id)
        return await self._repository.list_for_user(user_id=user_id)

    async def get_defaults(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceDefaults:
        """Return configured or fully inherited defaults for one workspace."""

        await self._tenant_service.require_access(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        defaults = await self._repository.get(workspace_id=workspace_id)
        if defaults is not None:
            return defaults
        return WorkspaceDefaults(
            workspace_id=workspace_id,
            model_target=None,
            harness=None,
            updated_at=self._clock(),
        )

    async def replace_defaults(
        self,
        *,
        user_id: str,
        model_target: ModelTarget | None,
        harness: PipelineHarness | None,
        workspace_id: str,
    ) -> WorkspaceDefaults:
        """Replace all workspace overrides after validating model routing."""

        await self._tenant_service.require_access(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        if model_target is not None:
            await self._linked_service_service.require_available_selection(
                workspace_id=workspace_id,
                service_id=model_target.linked_service_id,
                model_id=model_target.model_id,
            )
        return await self._repository.replace(
            defaults=WorkspaceDefaults(
                workspace_id=workspace_id,
                model_target=model_target,
                harness=harness,
                updated_at=self._clock(),
            ),
        )
