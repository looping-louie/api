"""Controller for listing Projects."""

from src.app.schemas.project import ProjectResponse
from src.app.services.projects.service import ProjectService

from .response import project_response


class ProjectListController:
    """List Projects accessible to the requesting User."""

    async def list_for_user(self, *, user_id: str) -> list[ProjectResponse]:
        """Return all Projects available to the requesting User."""

        return [
            project_response(project)
            for project in await self._project_service.list_for_user(
                user_id=user_id,
            )
        ]

    _project_service: ProjectService