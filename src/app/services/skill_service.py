from __future__ import annotations

from collections.abc import Mapping, Sequence

from .shared.instruction_service import (
    InstructionCreate,
    InstructionDocument,
    InstructionService,
    InstructionSummary,
    InstructionUpdate,
)
from .shared.tenant_service import TenantService


STRICTNESS_PHASES: frozenset[str] = frozenset(
    {
        "prototype",
        "mvp",
        "production",
    }
)


class SkillValidationError(Exception):
    """Raised when skill-specific metadata is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        super().__init__(f"Invalid skill field '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class SkillService:
    """Application service for skill operations."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        instruction_service: InstructionService,
    ) -> None:
        self._tenant_service = tenant_service
        self._instruction_service = instruction_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> list[InstructionSummary]:
        """List skills available in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._instruction_service.list(
            workspace_id=workspace_id,
            instruction_type="skill",
            search=search,
        )

    async def describe(
        self,
        *,
        user_id: str,
        skill_id: str,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Return a complete skill."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._instruction_service.describe(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=skill_id,
        )

    async def create(
        self,
        *,
        user_id: str,
        payload: InstructionCreate,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Create a skill in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        self._validate_metadata(payload.metadata)

        return await self._instruction_service.create(
            workspace_id=workspace_id,
            instruction_type="skill",
            payload=payload,
        )

    async def update(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: InstructionUpdate,
        requested_workspace_id: str | None = None,
    ) -> InstructionDocument:
        """Update an existing skill."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        if payload.metadata is not None:
            self._validate_metadata(payload.metadata)

        return await self._instruction_service.update(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=skill_id,
            payload=payload,
        )

    async def delete(
        self,
        *,
        user_id: str,
        skill_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Delete a skill when it has no blocking dependencies."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        await self._instruction_service.delete(
            workspace_id=workspace_id,
            instruction_type="skill",
            instruction_id=skill_id,
        )

    async def _resolve_workspace_id(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> str:
        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return tenant.workspace_id

    def _validate_metadata(self, metadata: Mapping[str, object]) -> None:
        applies_when = metadata.get("applies_when")

        if applies_when is not None:
            self._validate_applies_when(applies_when)

        default_strictness = metadata.get("default_strictness")

        if default_strictness is not None:
            self._validate_default_strictness(default_strictness)

    def _validate_applies_when(self, value: object) -> None:
        if not self._is_sequence(value):
            raise SkillValidationError(
                field_name="metadata.applies_when",
                message="must be a list of strings",
            )

        normalized_values: list[str] = []
        seen: set[str] = set()

        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise SkillValidationError(
                    field_name="metadata.applies_when",
                    message="must contain only non-empty strings",
                )

            normalized = item.strip()
            comparison_key = normalized.casefold()

            if comparison_key in seen:
                raise SkillValidationError(
                    field_name="metadata.applies_when",
                    message=f"contains duplicate value '{normalized}'",
                )

            seen.add(comparison_key)
            normalized_values.append(normalized)

        if not normalized_values:
            raise SkillValidationError(
                field_name="metadata.applies_when",
                message="must contain at least one value",
            )

    def _validate_default_strictness(self, value: object) -> None:
        if not isinstance(value, Mapping):
            raise SkillValidationError(
                field_name="metadata.default_strictness",
                message="must be an object",
            )

        unknown_phases = set(value) - STRICTNESS_PHASES

        if unknown_phases:
            phases = ", ".join(sorted(str(phase) for phase in unknown_phases))
            raise SkillValidationError(
                field_name="metadata.default_strictness",
                message=f"contains unsupported phases: {phases}",
            )

        for phase, strictness in value.items():
            self._validate_strictness_value(
                phase=str(phase),
                value=strictness,
            )

    @staticmethod
    def _validate_strictness_value(*, phase: str, value: object) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise SkillValidationError(
                field_name=f"metadata.default_strictness.{phase}",
                message="must be an integer between 0 and 100",
            )

        if value < 0 or value > 100:
            raise SkillValidationError(
                field_name=f"metadata.default_strictness.{phase}",
                message="must be between 0 and 100",
            )

    @staticmethod
    def _is_sequence(value: object) -> bool:
        return isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        )
