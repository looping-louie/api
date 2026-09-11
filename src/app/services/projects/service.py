"""Application service for projects."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from src.app.models.project import ProjectDocument
from src.app.repositories.projects import ProjectRepository
from src.app.services.linked_services import LinkedServiceService
from src.app.services.shared.tenant import TenantService
from src.app.services.users import UserService


class ProjectService:
    """Manage User-owned Projects."""

    def __init__(
        self,
        *,
        repository: ProjectRepository,
        tenant_service: TenantService,
        linked_service_service: LinkedServiceService,
        user_service: UserService,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        """Store project persistence and access-validation dependencies."""

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
    ) -> ProjectDocument:
        """Create a Project owned by an existing User."""

        await self._user_service.get(user_id=user_id)
        now = self._clock()
        return await self._repository.create(
            project=ProjectDocument(
                id=self._id_factory(),
                name=name,
                created_at=now,
                updated_at=now,
            ),
            owner_id=user_id,
        )

    async def list_for_user(self, *, user_id: str) -> list[ProjectDocument]:
        """Return Projects accessible to an existing User."""

        await self._user_service.get(user_id=user_id)
        return await self._repository.list_for_user(user_id=user_id)

    async def describe(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> ProjectDocument:
        """Return one Project accessible to the requesting User."""

        await self._tenant_service.require_access(
            user_id=user_id,
            project_id=project_id,
        )
        return await self._repository.get_project(project_id=project_id)

    async def update(
        self,
        *,
        user_id: str,
        project_id: str,
        name: str,
    ) -> ProjectDocument:
        """Update the mutable metadata for one accessible Project."""

        current = await self.describe(
            user_id=user_id,
            project_id=project_id,
        )
        return await self._repository.update_project(
            project=replace(
                current,
                name=name,
                updated_at=self._clock(),
            ),
        )
