"""Controller for patching Projects."""

from src.app.schemas.project import ProjectPatchRequest, ProjectResponse
from src.app.services.projects.service import ProjectService

from .response import project_response


class ProjectPatchController:
    """Apply mutable metadata changes to one Project."""

    async def patch(
        self,
        *,
        user_id: str,
        project_id: str,
        payload: ProjectPatchRequest,
    ) -> ProjectResponse:
        """Update mutable metadata for one accessible Project."""

        return project_response(await self._project_service.update(
            user_id=user_id,
            project_id=project_id,
            name=payload.name,
        ))

    _project_service: ProjectService
