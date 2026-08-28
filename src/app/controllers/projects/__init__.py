"""Controllers for Project HTTP operations."""

from src.app.services.projects.service import ProjectService

from .create import ProjectCreateController
from .describe import ProjectDescribeController
from .list import ProjectListController
from .patch import ProjectPatchController


class ProjectController(
    ProjectCreateController,
    ProjectListController,
    ProjectDescribeController,
    ProjectPatchController,
):
    """Compose endpoint-specific Project controllers."""

    def __init__(self, *, service: ProjectService) -> None:
        """Store the shared Project application service."""

        self._project_service = service


__all__ = [
    'ProjectController',
    'ProjectCreateController',
    'ProjectDescribeController',
    'ProjectListController',
    'ProjectPatchController',
]
