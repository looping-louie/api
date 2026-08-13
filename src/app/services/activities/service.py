"""Application service for activity definitions and changelog access."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Callable, Literal, cast

from pydantic import ValidationError

from src.app.models.activity import (
    ActivityChangelogEntry,
    ActivityDocument,
    ActivityType,
)
from src.app.repositories.activities.repository import ActivityRepository
from src.app.schemas.activity import validate_activity_config
from src.app.services.shared.pagination import PAGE_SIZE
from src.app.services.shared.tenant import TenantService


class ActivityNotFoundError(Exception):
    """Raised when an activity is absent from its resolved workspace."""

    def __init__(self, activity_id: str) -> None:
        """Store the missing activity identifier."""

        self.activity_id = activity_id


class ActivityValidationError(Exception):
    """Raised when an activity mutation fails domain validation."""

    def __init__(self, *, field_name: str, message: str) -> None:
        """Store the field-specific validation failure."""

        super().__init__(f"Invalid activity field '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class ActivityService:
    """Coordinate validated activity operations for one resolved workspace."""

    def __init__(self, *, repository: ActivityRepository, tenant_service: TenantService, id_factory: Callable[[], str], clock: Callable[[], datetime]) -> None:
        """Store persistence, tenancy, identifier, and time dependencies."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._clock = clock

    async def list(self, *, user_id: str, offset: int, requested_workspace_id: str | None = None) -> tuple[list[ActivityDocument], int]:
        """Return one fixed-size page of activities."""

        workspace_id = await self._workspace_id(user_id, requested_workspace_id)
        documents, total = await self._repository.list(workspace_id=workspace_id, offset=self._offset(offset), limit=PAGE_SIZE)
        return list(documents), total

    async def get(self, *, user_id: str, activity_id: str, requested_workspace_id: str | None = None) -> ActivityDocument:
        """Return one activity or raise the standard not-found error."""

        return await self._require(await self._workspace_id(user_id, requested_workspace_id), activity_id)

    async def create(self, *, user_id: str, title: str, description: str, activity_type: str, config: dict[str, object], requested_workspace_id: str | None = None) -> ActivityDocument:
        """Create a validated active activity and its initial changelog entry."""

        workspace_id = await self._workspace_id(user_id, requested_workspace_id)
        actor_id = self._text(user_id, 'user_id')
        now = self._clock()
        normalized_type = self._activity_type(activity_type)
        normalized_config = self._config(config, normalized_type)
        document = ActivityDocument(
            id=self._id_factory(), workspace_id=workspace_id, title=self._text(title, 'title'),
            description=description.strip(), status='active', type=normalized_type,
            config=normalized_config, created_at=now, created_by=actor_id, updated_at=now,
            updated_by=actor_id,
        )
        return await self._repository.create(document=document, changelog_entry=self._entry(document, actor_id, 'created', now, content=self._content(document)))

    async def patch(self, *, user_id: str, activity_id: str, changes: dict[str, object], requested_workspace_id: str | None = None) -> ActivityDocument:
        """Apply mutable fields and append an activity changelog entry."""

        workspace_id = await self._workspace_id(user_id, requested_workspace_id)
        current = await self._require(workspace_id, activity_id)
        actor_id = self._text(user_id, 'user_id')
        config = (
            self._config(changes['config'], current.type)
            if 'config' in changes
            else current.config
        )
        updated = replace(
            current, title=self._text(changes['title'], 'title') if 'title' in changes else current.title,
            description=str(changes['description']).strip() if 'description' in changes else current.description,
            status=changes.get('status', current.status), type=current.type, config=config,
            updated_at=self._clock(), updated_by=actor_id,
        )
        diff = {field: getattr(updated, field) for field in changes if getattr(current, field) != getattr(updated, field)}
        if not diff:
            raise ActivityValidationError(
                field_name='body',
                message='must produce at least one effective change',
            )
        change_type = self._change_type(current.status, updated.status)
        if not await self._repository.update(document=updated, changelog_entry=self._entry(updated, actor_id, change_type, updated.updated_at, diff=diff)):
            raise ActivityNotFoundError(activity_id)
        return updated

    async def delete(self, *, user_id: str, activity_id: str, requested_workspace_id: str | None = None) -> None:
        """Delete an activity while retaining its terminal changelog entry."""

        workspace_id = await self._workspace_id(user_id, requested_workspace_id)
        document = await self._require(workspace_id, activity_id)
        actor_id = self._text(user_id, 'user_id')
        if not await self._repository.delete(workspace_id=workspace_id, activity_id=activity_id, changelog_entry=self._entry(document, actor_id, 'deleted', self._clock(), content=self._content(document))):
            raise ActivityNotFoundError(activity_id)

    async def list_changelog(self, *, user_id: str, activity_id: str, offset: int, requested_workspace_id: str | None = None) -> tuple[list[ActivityChangelogEntry], int]:
        """Return one fixed-size activity changelog page."""

        workspace_id = await self._workspace_id(user_id, requested_workspace_id)
        entries, total = await self._repository.list_changelog(workspace_id=workspace_id, activity_id=activity_id, offset=self._offset(offset), limit=PAGE_SIZE)
        return list(entries), total

    async def _workspace_id(self, user_id: str, requested_workspace_id: str | None) -> str:
        """Resolve the selected workspace for a user."""

        context = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return context.workspace_id

    async def _require(self, workspace_id: str, activity_id: str) -> ActivityDocument:
        """Return an existing activity or raise a resource-specific error."""

        document = await self._repository.get(workspace_id=workspace_id, activity_id=activity_id)
        if document is None:
            raise ActivityNotFoundError(activity_id)
        return document

    def _entry(self, document: ActivityDocument, actor_id: str, change_type: Literal['created', 'updated', 'enabled', 'disabled', 'archived', 'deleted'], changed_at: datetime, *, diff: dict[str, object] | None = None, content: dict[str, object] | None = None) -> ActivityChangelogEntry:
        """Build one immutable activity history entry."""

        return ActivityChangelogEntry(id=self._id_factory(), activity_id=document.id, workspace_id=document.workspace_id, change_type=change_type, actor_id=actor_id, changed_at=changed_at, diff=diff, content=content)

    @staticmethod
    def _config(value: object, activity_type: ActivityType) -> dict[str, object]:
        """Validate a config using the owning immutable Activity type."""

        try:
            return validate_activity_config(
                activity_type=activity_type,
                value=value,
            ).model_dump(by_alias=True)
        except ValidationError as error:
            raise ActivityValidationError(
                field_name='config',
                message=error.errors()[0]['msg'],
            ) from error

    @staticmethod
    def _activity_type(value: object) -> ActivityType:
        """Validate a supported top-level activity discriminator."""

        if value not in (
            'approval',
            'quiz',
            'direct_loop',
            'refinement_loop',
            'roundtable_loop',
        ):
            raise ActivityValidationError(
                field_name='type',
                message='must contain a supported activity type',
            )
        return cast(ActivityType, value)

    @staticmethod
    def _content(document: ActivityDocument) -> dict[str, object]:
        """Return a complete immutable representation for history entries."""

        return {'title': document.title, 'description': document.description, 'status': document.status, 'type': document.type, 'config': document.config}

    @staticmethod
    def _text(value: object, field_name: str) -> str:
        """Normalize a required non-empty text field."""

        if not isinstance(value, str) or not value.strip():
            raise ActivityValidationError(
                field_name=field_name,
                message='must be a non-empty string',
            )
        return value.strip()

    @staticmethod
    def _offset(value: int) -> int:
        """Validate a non-negative pagination offset."""

        if value < 0:
            raise ActivityValidationError(
                field_name='offset',
                message='must be non-negative',
            )
        return value

    @staticmethod
    def _change_type(before: str, after: str) -> Literal['updated', 'enabled', 'disabled', 'archived']:
        """Select the changelog type for a status transition."""

        if before != after:
            return after if after in ('enabled', 'disabled', 'archived') else 'updated'
        return 'updated'
