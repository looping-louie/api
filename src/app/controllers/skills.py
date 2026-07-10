"""HTTP controllers for reusable reviewer skills."""

from typing import NoReturn

from fastapi import HTTPException, status

from src.app.schemas.skills import (
    SkillCreateRequest,
    SkillResponse,
    SkillSummaryResponse,
    SkillUpdateRequest,
)
from src.app.services.service_factory import get_skill_service
from src.app.services.skills.skill_document_service import SkillDocumentError
from src.app.services.skills.skill_service import (
    SkillConflictError,
    SkillNotFoundError,
)


_skill_service = get_skill_service()


async def list_skills(
    include_deleted: bool = False,
) -> list[SkillResponse]:
    """Return merged built-in and organisation-owned skills."""

    try:
        skills = await _skill_service.list_skills(
            include_deleted=include_deleted
        )
    except SkillDocumentError as exc:
        _raise_http_error(exc)

    return [
        SkillSummaryResponse.model_validate(skill)
        for skill in skills
    ]


async def get_skill(skill_id: str) -> SkillResponse:
    """Return one active skill."""

    try:
        skill = await _skill_service.get_skill(skill_id)
    except (
        SkillDocumentError,
        SkillNotFoundError,
    ) as exc:
        _raise_http_error(exc)

    return SkillResponse.model_validate(skill)


async def create_skill(
    request: SkillCreateRequest,
) -> SkillResponse:
    """Create an organisation-owned skill."""

    try:
        skill = await _skill_service.create_skill(
            skill_id=request.skill_id,
            name=request.name,
            description=request.description,
            content=request.content,
            metadata=request.metadata,
        )
    except (
        SkillDocumentError,
        SkillConflictError,
    ) as exc:
        _raise_http_error(exc)

    return SkillResponse.model_validate(skill)


async def update_skill(
    skill_id: str,
    request: SkillUpdateRequest,
) -> SkillResponse:
    """Edit a custom skill or create a built-in override."""

    try:
        skill = await _skill_service.update_skill(
            skill_id=skill_id,
            name=request.name,
            description=request.description,
            content=request.content,
            metadata=request.metadata,
        )
    except (
        SkillDocumentError,
        SkillNotFoundError,
        SkillConflictError,
    ) as exc:
        _raise_http_error(exc)

    return SkillResponse.model_validate(skill)


async def delete_skill(skill_id: str) -> None:
    """Hide a built-in or soft-delete a custom skill."""

    try:
        await _skill_service.delete_skill(skill_id)
    except (
        SkillDocumentError,
        SkillNotFoundError,
    ) as exc:
        _raise_http_error(exc)


async def restore_skill(skill_id: str) -> SkillResponse:
    """Restore a custom skill or revert a built-in override."""

    try:
        skill = await _skill_service.restore_skill(skill_id)
    except (
        SkillDocumentError,
        SkillNotFoundError,
        SkillConflictError,
    ) as exc:
        _raise_http_error(exc)

    return SkillResponse.model_validate(skill)


def _raise_http_error(exc: Exception) -> NoReturn:
    """Map skill errors to safe HTTP responses."""

    if isinstance(exc, SkillNotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, SkillConflictError):
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_400_BAD_REQUEST

    raise HTTPException(
        status_code=code,
        detail=str(exc),
    ) from exc
