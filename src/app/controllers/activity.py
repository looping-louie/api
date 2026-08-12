"""Controller for activity HTTP operations."""

from __future__ import annotations

from src.app.schemas.activity import (
    ActivityChangelogListResponse, ActivityChangelogEntryResponse, ActivityCreateRequest,
    ActivityListResponse, ActivityPatchRequest, ActivityResponse,
)
from src.app.schemas.shared import DeleteResponse
from src.app.services.activities.service import ActivityService


class ActivityController:
    """Translate activity HTTP schemas to and from the application service."""

    def __init__(self, *, activity_service: ActivityService) -> None:
        """Store the shared activity service."""

        self._activity_service = activity_service

    async def list(self, *, user_id: str, offset: int, requested_workspace_id: str | None = None) -> ActivityListResponse:
        """Return one activity page."""

        documents, total = await self._activity_service.list(user_id=user_id, offset=offset, requested_workspace_id=requested_workspace_id)
        return ActivityListResponse(items=[ActivityResponse.model_validate(item) for item in documents], total=total)

    async def get(self, *, user_id: str, activity_id: str, requested_workspace_id: str | None = None) -> ActivityResponse:
        """Return one activity."""

        return ActivityResponse.model_validate(await self._activity_service.get(user_id=user_id, activity_id=activity_id, requested_workspace_id=requested_workspace_id))

    async def create(self, *, user_id: str, payload: ActivityCreateRequest, requested_workspace_id: str | None = None) -> ActivityResponse:
        """Create one activity."""

        document = await self._activity_service.create(user_id=user_id, title=payload.title, description=payload.description, config=payload.config.model_dump(by_alias=True), requested_workspace_id=requested_workspace_id)
        return ActivityResponse.model_validate(document)

    async def patch(self, *, user_id: str, activity_id: str, payload: ActivityPatchRequest, requested_workspace_id: str | None = None) -> ActivityResponse:
        """Apply supplied activity fields."""

        changes = payload.model_dump(exclude_unset=True)
        if 'config' in changes:
            changes['config'] = payload.config.model_dump(by_alias=True)
        document = await self._activity_service.patch(user_id=user_id, activity_id=activity_id, changes=changes, requested_workspace_id=requested_workspace_id)
        return ActivityResponse.model_validate(document)

    async def delete(self, *, user_id: str, activity_id: str, requested_workspace_id: str | None = None) -> DeleteResponse:
        """Delete one activity."""

        await self._activity_service.delete(user_id=user_id, activity_id=activity_id, requested_workspace_id=requested_workspace_id)
        return DeleteResponse()

    async def list_changelog(self, *, user_id: str, activity_id: str, offset: int, requested_workspace_id: str | None = None) -> ActivityChangelogListResponse:
        """Return one activity changelog page."""

        entries, total = await self._activity_service.list_changelog(user_id=user_id, activity_id=activity_id, offset=offset, requested_workspace_id=requested_workspace_id)
        return ActivityChangelogListResponse(items=[ActivityChangelogEntryResponse.model_validate(entry) for entry in entries], total=total)