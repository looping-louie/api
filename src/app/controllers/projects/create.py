"""Controller for creating Projects."""

from src.app.schemas.project import ProjectCreateRequest, ProjectResponse
from src.app.services.projects.service import ProjectService

from .response import project_response


class ProjectCreateController:
    """Create one Project for the requesting User."""

    async def create(
        self,
        *,
        user_id: str,
        payload: ProjectCreateRequest,
    ) -> ProjectResponse:
        """Create one Project owned by the requesting User."""

        return project_response(await self._project_service.create(
            user_id=user_id,
            name=payload.name,
        ))

    _project_service: ProjectService
