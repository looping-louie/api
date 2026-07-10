"""Application service for built-in, custom and overridden skills."""

from datetime import datetime, timezone
from uuid import uuid4

from src.app.models.skills import (
    BuiltinSkill,
    SkillState,
    StoredSkill,
)
from src.app.repositories.skill_repository import SkillRepository
from src.app.services.providers.request_context_service import RequestContextService
from src.app.services.skills.skill_document_service import SkillDocumentService


class SkillError(Exception):
    """Base error for skill operations."""


class SkillNotFoundError(SkillError):
    """Raised when a skill does not exist or is hidden."""


class SkillConflictError(SkillError):
    """Raised when a skill operation conflicts with existing state."""


class SkillDeletedError(SkillConflictError):
    """Raised when a deleted skill must be restored first."""


class SkillService:
    """Merge built-ins with organisation customisations."""

    def __init__(
        self,
        repository: SkillRepository,
        document_service: SkillDocumentService,
        request_context: RequestContextService,
    ) -> None:
        """Store skill infrastructure dependencies."""

        self._repository = repository
        self._documents = document_service
        self._request_context = request_context

    async def list_skills(
        self,
        include_deleted: bool = False,
    ) -> list[SkillState]:
        """Return built-ins, overrides and custom skills."""

        actor = self._request_context.get_current_actor()
        builtins = self._documents.list_builtin_skills()
        stored = await self._repository.list_for_org(actor.org_id)
        stored_by_id = {
            skill.skill_id: skill
            for skill in stored
        }
        states: list[SkillState] = []
        consumed_ids: set[str] = set()

        for builtin in builtins:
            row = stored_by_id.get(builtin.skill_id)
            consumed_ids.add(builtin.skill_id)
            state = self._merge_builtin(builtin, row)

            if include_deleted or not state.deleted:
                states.append(state)

        for row in stored:
            if row.skill_id in consumed_ids:
                continue

            state = self._state_from_stored(row)

            if include_deleted or not state.deleted:
                states.append(state)

        return sorted(
            states,
            key=lambda skill: (
                0 if skill.source == "built_in" else 1,
                skill.name.lower(),
                skill.skill_id,
            ),
        )

    async def get_skill(self, skill_id: str) -> SkillState:
        """Return one active merged skill."""

        normalised_id = self._documents.validate_skill_id(skill_id)
        actor = self._request_context.get_current_actor()
        builtin = self._documents.get_builtin_skill(normalised_id)
        stored = await self._repository.get(
            actor.org_id,
            normalised_id,
        )
        state = self._resolve_state(builtin, stored)

        if state is None or state.deleted:
            raise SkillNotFoundError(
                f"Skill '{normalised_id}' was not found."
            )

        return state

    async def create_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        content: str,
        metadata: dict,
    ) -> SkillState:
        """Create one organisation-owned custom skill."""

        validated = self._documents.validate_write(
            skill_id=skill_id,
            name=name,
            description=description,
            content=content,
            metadata=metadata,
        )
        actor = self._request_context.get_current_actor()
        builtin = self._documents.get_builtin_skill(
            validated.skill_id
        )
        stored = await self._repository.get(
            actor.org_id,
            validated.skill_id,
        )

        if builtin is not None or stored is not None:
            raise SkillConflictError(
                f"Skill '{validated.skill_id}' already exists."
            )

        now = datetime.now(timezone.utc)
        created = await self._repository.upsert(
            StoredSkill(
                id=uuid4().hex,
                org_id=actor.org_id,
                skill_id=validated.skill_id,
                name=validated.name,
                description=validated.description,
                content=validated.content,
                metadata=validated.metadata,
                source="custom",
                base_skill_id=None,
                created_by=actor.user_id,
                created_at=now,
                updated_by=actor.user_id,
                updated_at=now,
                deleted_at=None,
            )
        )

        return self._state_from_stored(created)

    async def update_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        content: str,
        metadata: dict,
    ) -> SkillState:
        """Update a custom skill or create a built-in override."""

        normalised_id = self._documents.validate_skill_id(skill_id)
        validated = self._documents.validate_write(
            skill_id=normalised_id,
            name=name,
            description=description,
            content=content,
            metadata=metadata,
        )
        actor = self._request_context.get_current_actor()
        builtin = self._documents.get_builtin_skill(normalised_id)
        stored = await self._repository.get(
            actor.org_id,
            normalised_id,
        )

        if stored is not None and stored.deleted_at is not None:
            raise SkillDeletedError(
                f"Restore skill '{normalised_id}' before editing it."
            )

        if builtin is None and stored is None:
            raise SkillNotFoundError(
                f"Skill '{normalised_id}' was not found."
            )

        now = datetime.now(timezone.utc)
        source = stored.source if stored is not None else "override"
        base_skill_id = (
            stored.base_skill_id
            if stored is not None
            else normalised_id
        )
        updated = await self._repository.upsert(
            StoredSkill(
                id=stored.id if stored else uuid4().hex,
                org_id=actor.org_id,
                skill_id=normalised_id,
                name=validated.name,
                description=validated.description,
                content=validated.content,
                metadata=validated.metadata,
                source=source,
                base_skill_id=base_skill_id,
                created_by=(
                    stored.created_by
                    if stored is not None
                    else actor.user_id
                ),
                created_at=stored.created_at if stored else now,
                updated_by=actor.user_id,
                updated_at=now,
                deleted_at=None,
            )
        )

        return self._state_from_stored(updated)

    async def delete_skill(self, skill_id: str) -> None:
        """Hide a built-in or soft-delete a custom skill."""

        normalised_id = self._documents.validate_skill_id(skill_id)
        actor = self._request_context.get_current_actor()
        builtin = self._documents.get_builtin_skill(normalised_id)
        stored = await self._repository.get(
            actor.org_id,
            normalised_id,
        )
        now = datetime.now(timezone.utc)

        if stored is not None:
            if stored.deleted_at is not None:
                return

            await self._repository.mark_deleted(
                org_id=actor.org_id,
                skill_id=normalised_id,
                updated_by=actor.user_id,
                updated_at=now,
            )
            return

        if builtin is None:
            raise SkillNotFoundError(
                f"Skill '{normalised_id}' was not found."
            )

        await self._repository.upsert(
            self._build_override_tombstone(
                actor.org_id,
                actor.user_id,
                builtin,
                now,
            )
        )

    async def restore_skill(self, skill_id: str) -> SkillState:
        """Restore a custom skill or revert a built-in to source."""

        normalised_id = self._documents.validate_skill_id(skill_id)
        actor = self._request_context.get_current_actor()
        builtin = self._documents.get_builtin_skill(normalised_id)
        stored = await self._repository.get(
            actor.org_id,
            normalised_id,
        )

        if stored is None:
            if builtin is None:
                raise SkillNotFoundError(
                    f"Skill '{normalised_id}' was not found."
                )

            return self._state_from_builtin(builtin)

        if stored.source == "override":
            if builtin is None:
                raise SkillConflictError(
                    "Cannot restore an override whose built-in source "
                    "no longer exists."
                )

            await self._repository.hard_delete(
                org_id=actor.org_id,
                skill_id=normalised_id,
            )

            return self._state_from_builtin(builtin)

        if stored.deleted_at is None:
            return self._state_from_stored(stored)

        restored = await self._repository.restore_custom(
            org_id=actor.org_id,
            skill_id=normalised_id,
            updated_by=actor.user_id,
            updated_at=datetime.now(timezone.utc),
        )

        return self._state_from_stored(restored)

    @staticmethod
    def _build_override_tombstone(
        org_id: str,
        user_id: str,
        builtin: BuiltinSkill,
        now: datetime,
    ) -> StoredSkill:
        """Create a deletion marker for one built-in skill."""

        return StoredSkill(
            id=uuid4().hex,
            org_id=org_id,
            skill_id=builtin.skill_id,
            name=builtin.name,
            description=builtin.description,
            content=builtin.content,
            metadata=builtin.metadata,
            source="override",
            base_skill_id=builtin.skill_id,
            created_by=user_id,
            created_at=now,
            updated_by=user_id,
            updated_at=now,
            deleted_at=now,
        )

    def _resolve_state(
        self,
        builtin: BuiltinSkill | None,
        stored: StoredSkill | None,
    ) -> SkillState | None:
        """Resolve one logical skill from source and stored state."""

        if builtin is not None:
            return self._merge_builtin(builtin, stored)

        if stored is not None:
            return self._state_from_stored(stored)

        return None

    def _merge_builtin(
        self,
        builtin: BuiltinSkill,
        stored: StoredSkill | None,
    ) -> SkillState:
        """Apply an organisation row over one built-in skill."""

        if stored is None:
            return self._state_from_builtin(builtin)

        return self._state_from_stored(stored)

    @staticmethod
    def _state_from_builtin(builtin: BuiltinSkill) -> SkillState:
        """Build an API state from a built-in file."""

        return SkillState(
            skill_id=builtin.skill_id,
            name=builtin.name,
            description=builtin.description,
            content=builtin.content,
            metadata=builtin.metadata,
            source="built_in",
            base_skill_id=None,
            editable=True,
            deleted=False,
            created_by=None,
            created_at=None,
            updated_by=None,
            updated_at=None,
        )

    @staticmethod
    def _state_from_stored(stored: StoredSkill) -> SkillState:
        """Build an API state from a database row."""

        return SkillState(
            skill_id=stored.skill_id,
            name=stored.name,
            description=stored.description,
            content=stored.content,
            metadata=stored.metadata,
            source=stored.source,
            base_skill_id=stored.base_skill_id,
            editable=True,
            deleted=stored.deleted_at is not None,
            created_by=stored.created_by,
            created_at=stored.created_at,
            updated_by=stored.updated_by,
            updated_at=stored.updated_at,
        )
