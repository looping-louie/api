"""Project HTTP response mapping."""

from src.app.models.project import ProjectDocument
from src.app.schemas.project import ProjectResponse


def project_response(project: ProjectDocument) -> ProjectResponse:
    """Map a Project document to its public representation."""

    return ProjectResponse(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
