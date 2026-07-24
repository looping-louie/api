"""SQL-backed instruction library consumed by execution runtimes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from src.app.catalogs.instructions import InstructionOrigin

from .shared.instruction_service import (
    AvailableInstructionDocument,
    InstructionRepository,
    InstructionType,
)
from .shared.tenant_service import TenantService
from .persona_service import PersonaSkillRepository


DEFAULT_AGENT_ROLES = ("generator", "reviewer")
DEFAULT_STRICTNESS = {
    "prototype": 50,
    "mvp": 50,
    "production": 50,
}


class ExecutionInstructionNotFoundError(LookupError):
    """Raised when an execution references an unavailable instruction."""

    def __init__(
        self,
        *,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> None:
        super().__init__(
            f"{instruction_type.title()} '{instruction_id}' is not "
            "available for execution."
        )
        self.instruction_type = instruction_type
        self.instruction_id = instruction_id


@dataclass(frozen=True, slots=True)
class ExecutionInstruction:
    """One selectable SQL instruction prepared for prompt assembly."""

    id: str
    source_id: str
    instruction_type: InstructionType
    origin: InstructionOrigin
    version: int
    catalog_version: int | None
    name: str
    description: str
    content: str
    metadata: Mapping[str, object]
    skill_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExecutionInstructionLibrary:
    """Immutable workspace snapshot used throughout one execution."""

    workspace_id: str
    skills: Mapping[str, ExecutionInstruction]
    personas: Mapping[str, ExecutionInstruction]
    skill_aliases: Mapping[str, str]
    persona_aliases: Mapping[str, str]

    def snapshot(self) -> dict[str, object]:
        """Serialize every definition visible when the execution started."""

        instructions = [
            self._snapshot_entry(instruction)
            for instruction in (
                *self.skills.values(),
                *self.personas.values(),
            )
        ]
        instructions.sort(
            key=lambda item: (
                str(item["instruction_type"]),
                str(item["id"]),
            )
        )

        return {
            "snapshot_version": 1,
            "workspace_id": self.workspace_id,
            "instructions": instructions,
        }

    def skill_registry(self) -> list[dict[str, object]]:
        """Return planner metadata for every selectable skill."""

        return [
            self._skill_registry_entry(instruction)
            for instruction in self.skills.values()
        ]

    def persona_registry(self) -> list[dict[str, object]]:
        """Return planner metadata for every selectable persona."""

        available_skill_ids = set(self.skills)
        return [
            self._persona_registry_entry(
                instruction,
                available_skill_ids=available_skill_ids,
            )
            for instruction in self.personas.values()
        ]

    def normalize_skill_id(self, instruction_id: str) -> str:
        """Return the runtime ID for a stable ID or builtin short key."""

        return self._normalize_id(
            instruction_id=instruction_id,
            aliases=self.skill_aliases,
            instruction_type="skill",
        )

    def normalize_persona_id(self, instruction_id: str) -> str:
        """Return the runtime ID for a stable ID or builtin short key."""

        return self._normalize_id(
            instruction_id=instruction_id,
            aliases=self.persona_aliases,
            instruction_type="persona",
        )

    def persona_content(self, instruction_id: str) -> str:
        """Resolve already-loaded persona content."""

        runtime_id = self.normalize_persona_id(instruction_id)
        return self.personas[runtime_id].content

    def skill_contents(
        self,
        instruction_ids: Sequence[str],
    ) -> list[str]:
        """Resolve already-loaded skill content in input order."""

        return [
            self.skills[self.normalize_skill_id(instruction_id)].content
            for instruction_id in instruction_ids
        ]

    def _skill_registry_entry(
        self,
        instruction: ExecutionInstruction,
    ) -> dict[str, object]:
        metadata = instruction.metadata
        return {
            "id": instruction.id,
            "description": (
                instruction.description.strip()
                or instruction.name
            ),
            "applies_when": self._string_list(
                metadata.get("applies_when"),
                default=[instruction.name],
            ),
            "applies_to": self._roles(metadata.get("applies_to")),
            "reviewer_default_strictness": self._strictness(
                metadata.get("reviewer_default_strictness")
                or metadata.get("default_strictness")
            ),
        }

    @staticmethod
    def _snapshot_entry(
        instruction: ExecutionInstruction,
    ) -> dict[str, object]:
        snapshot: dict[str, object] = {
            "id": instruction.source_id,
            "runtime_id": instruction.id,
            "instruction_type": instruction.instruction_type,
            "origin": instruction.origin.value,
            "version": instruction.version,
            "catalog_version": instruction.catalog_version,
            "name": instruction.name,
            "description": instruction.description,
            "content": instruction.content,
            "metadata": deepcopy(dict(instruction.metadata)),
        }
        if instruction.instruction_type == "persona":
            snapshot["skill_ids"] = list(instruction.skill_ids)
        return snapshot

    def _persona_registry_entry(
        self,
        instruction: ExecutionInstruction,
        *,
        available_skill_ids: set[str],
    ) -> dict[str, object]:
        metadata = instruction.metadata
        applies_to = self._roles(metadata.get("applies_to"))
        skills = []

        for skill_id in instruction.skill_ids:
            runtime_id = self.skill_aliases.get(skill_id)

            if (
                runtime_id is not None
                and runtime_id in available_skill_ids
                and runtime_id not in skills
            ):
                skills.append(runtime_id)

        default_for = [
            role
            for role in self._string_list(
                metadata.get("default_for"),
                default=[],
            )
            if role in applies_to
        ]

        return {
            "id": instruction.id,
            "description": (
                instruction.description.strip()
                or instruction.name
            ),
            "applies_when": self._string_list(
                metadata.get("applies_when"),
                default=[instruction.name],
            ),
            "applies_to": applies_to,
            "skills": skills,
            "default_for": default_for,
        }

    @staticmethod
    def _normalize_id(
        *,
        instruction_id: str,
        aliases: Mapping[str, str],
        instruction_type: InstructionType,
    ) -> str:
        normalized = instruction_id.strip()
        runtime_id = aliases.get(normalized)

        if runtime_id is None:
            raise ExecutionInstructionNotFoundError(
                instruction_type=instruction_type,
                instruction_id=normalized,
            )

        return runtime_id

    @staticmethod
    def _roles(value: object) -> list[str]:
        roles = ExecutionInstructionLibrary._string_list(
            value,
            default=list(DEFAULT_AGENT_ROLES),
        )
        supported = [
            role
            for role in roles
            if role in DEFAULT_AGENT_ROLES
        ]
        return supported or list(DEFAULT_AGENT_ROLES)

    @staticmethod
    def _strictness(value: object) -> dict[str, int]:
        if not isinstance(value, Mapping):
            return dict(DEFAULT_STRICTNESS)

        result: dict[str, int] = {}

        for phase, fallback in DEFAULT_STRICTNESS.items():
            candidate = value.get(phase)
            result[phase] = (
                candidate
                if (
                    isinstance(candidate, int)
                    and not isinstance(candidate, bool)
                    and 0 <= candidate <= 100
                )
                else fallback
            )

        return result

    @staticmethod
    def _string_list(
        value: object,
        *,
        default: list[str],
    ) -> list[str]:
        if not isinstance(value, Sequence) or isinstance(
            value,
            (str, bytes, bytearray),
        ):
            return list(default)

        result = [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]
        return list(dict.fromkeys(result)) or list(default)


class ExecutionInstructionLibraryService:
    """Loads the selectable instruction library from SQL per execution."""

    def __init__(
        self,
        *,
        repository: InstructionRepository,
        persona_skill_repository: PersonaSkillRepository,
        tenant_service: TenantService,
    ) -> None:
        self._repository = repository
        self._persona_skill_repository = persona_skill_repository
        self._tenant_service = tenant_service

    async def load(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
    ) -> ExecutionInstructionLibrary:
        """Load a fresh immutable snapshot for the resolved workspace."""

        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        workspace_id = tenant.workspace_id
        skills = await self._load_type(
            workspace_id=workspace_id,
            instruction_type="skill",
        )
        personas = await self._load_type(
            workspace_id=workspace_id,
            instruction_type="persona",
        )
        skill_aliases = self._build_aliases(skills)
        persona_aliases = self._build_aliases(personas)

        return ExecutionInstructionLibrary(
            workspace_id=workspace_id,
            skills=MappingProxyType(
                {
                    instruction.id: instruction
                    for instruction in skills
                }
            ),
            personas=MappingProxyType(
                {
                    instruction.id: instruction
                    for instruction in personas
                }
            ),
            skill_aliases=MappingProxyType(skill_aliases),
            persona_aliases=MappingProxyType(persona_aliases),
        )

    async def _load_type(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
    ) -> tuple[ExecutionInstruction, ...]:
        summaries = await self._repository.list_available_for_workspace(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
        )
        documents: list[AvailableInstructionDocument] = []

        for summary in summaries:
            if not summary.selectable:
                continue

            document = await (
                self._repository.get_available_for_workspace(
                    workspace_id=workspace_id,
                    instruction_type=instruction_type,
                    instruction_id=summary.id,
                )
            )

            if document is not None and document.selectable:
                documents.append(document)

        instructions: list[ExecutionInstruction] = []

        for document in documents:
            skill_ids = (
                await self._persona_skill_repository.list_for_persona(
                    persona_id=document.id,
                )
                if instruction_type == "persona"
                else ()
            )
            instructions.append(
                ExecutionInstruction(
                    id=self._runtime_id(document),
                    source_id=document.id,
                    instruction_type=document.instruction_type,
                    origin=document.origin,
                    version=document.version,
                    catalog_version=document.catalog_version,
                    name=document.name,
                    description=document.description,
                    content=document.instructions,
                    metadata=MappingProxyType(
                        deepcopy(dict(document.metadata))
                    ),
                    skill_ids=skill_ids,
                )
            )

        return tuple(instructions)

    @staticmethod
    def _runtime_id(
        document: AvailableInstructionDocument,
    ) -> str:
        if document.origin == InstructionOrigin.BUILTIN:
            return document.id.rsplit(":", maxsplit=1)[-1]

        return document.id

    @staticmethod
    def _build_aliases(
        instructions: Sequence[ExecutionInstruction],
    ) -> dict[str, str]:
        aliases: dict[str, str] = {}

        for instruction in instructions:
            aliases[instruction.id] = instruction.id
            aliases[instruction.source_id] = instruction.id

        return aliases


__all__ = [
    "ExecutionInstruction",
    "ExecutionInstructionLibrary",
    "ExecutionInstructionLibraryService",
    "ExecutionInstructionNotFoundError",
]
