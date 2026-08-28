"""Controller for describing Projects."""

from src.app.schemas.project import ProjectResponse
from src.app.services.projects.service import ProjectService

from .response import project_response


class ProjectDescribeController:
    """Describe one Project accessible to the requesting User."""

    async def describe(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> ProjectResponse:
        """Return one Project accessible to the requesting User."""

        return project_response(await self._project_service.describe(
            user_id=user_id,
            project_id=project_id,
        ))

    _project_service: ProjectService