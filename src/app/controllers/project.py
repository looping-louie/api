"""HTTP controller for projects."""

from __future__ import annotations

from src.app.models.project import ProjectDocument
from src.app.schemas.project import (
    ProjectCreateRequest,
    ProjectPatchRequest,
    ProjectResponse,
)
from src.app.services.projects.service import ProjectService


class ProjectController:
    """Translate Project HTTP contracts to application operations."""

    def __init__(self, *, service: ProjectService) -> None:
        """Store the Project application service."""

        self._service = service

    async def create(
        self,
        *,
        user_id: str,
        payload: ProjectCreateRequest,
    ) -> ProjectResponse:
        """Create one Project owned by the requesting User."""

        return self._project_response(await self._service.create(
            user_id=user_id,
            name=payload.name,
        ))

    async def list_for_user(self, *, user_id: str) -> list[ProjectResponse]:
        """Return all Projects available to the requesting User."""

        return [
            self._project_response(project)
            for project in await self._service.list_for_user(user_id=user_id)
        ]

    async def describe(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> ProjectResponse:
        """Return one Project accessible to the requesting User."""

        return self._project_response(await self._service.describe(
            user_id=user_id,
            project_id=project_id,
        ))

    async def patch(
        self,
        *,
        user_id: str,
        project_id: str,
        payload: ProjectPatchRequest,
    ) -> ProjectResponse:
        """Update mutable metadata for one accessible Project."""

        return self._project_response(await self._service.update(
            user_id=user_id,
            project_id=project_id,
            name=payload.name,
        ))

    @staticmethod
    def _project_response(project: ProjectDocument) -> ProjectResponse:
        """Map a Project document to its public representation."""

        return ProjectResponse(
            id=project.id,
            name=project.name,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
