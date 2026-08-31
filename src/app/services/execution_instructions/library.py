"""SQL-backed instruction library consumed by execution runtimes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from src.app.catalogs.persona_skills import InstructionOrigin

from ..persona_skills import (
    AvailableDefinitionDocument,
    DefinitionRepository,
    DefinitionType,
)
from ..shared.tenant import TenantService
from ..personas.types import (
    PersonaSkillRepository,
)


class ExecutionInstructionNotFoundError(LookupError):
    """Raised when an execution references an unavailable instruction."""

    def __init__(
        self,
        *,
        instruction_type: DefinitionType,
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
    instruction_type: DefinitionType
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

    project_id: str
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
            "project_id": self.project_id,
            "instructions": instructions,
        }

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

    def agent_snapshot(self, persona_id: str) -> dict[str, object]:
        """Serialize one Persona and its ordered Skills for a frozen run."""

        runtime_id = self.normalize_persona_id(persona_id)
        persona = self.personas[runtime_id]
        return {
            "snapshot_version": 1,
            "persona": self._snapshot_entry(persona),
            "skills": [
                self._snapshot_entry(
                    self.skills[self.normalize_skill_id(skill_id)]
                )
                for skill_id in persona.skill_ids
            ],
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

    @staticmethod
    def _normalize_id(
        *,
        instruction_id: str,
        aliases: Mapping[str, str],
        instruction_type: DefinitionType,
    ) -> str:
        normalized = instruction_id.strip()
        runtime_id = aliases.get(normalized)

        if runtime_id is None:
            raise ExecutionInstructionNotFoundError(
                instruction_type=instruction_type,
                instruction_id=normalized,
            )

        return runtime_id


class ExecutionInstructionLibraryService:
    """Loads the selectable instruction library from SQL per execution."""

    def __init__(
        self,
        *,
        repository: DefinitionRepository,
        persona_skill_repository: PersonaSkillRepository,
        tenant_service: TenantService,
        persona_repository: DefinitionRepository | None = None,
    ) -> None:
        """Store User instruction repositories and Project resolution."""

        self._repository = repository
        self._persona_repository = persona_repository or repository
        self._persona_skill_repository = persona_skill_repository
        self._tenant_service = tenant_service

    async def load(
        self,
        *,
        user_id: str,
        requested_project_id: str | None = None,
    ) -> ExecutionInstructionLibrary:
        """Load User instructions for one resolved execution Project."""

        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_project_id=requested_project_id,
        )
        project_id = tenant.project_id
        skills = await self._load_type(
            repository=self._repository,
            project_id=user_id,
            instruction_type="skill",
        )
        personas = await self._load_type(
            repository=self._persona_repository,
            project_id=user_id,
            instruction_type="persona",
        )
        skill_aliases = self._build_aliases(skills)
        persona_aliases = self._build_aliases(personas)

        return ExecutionInstructionLibrary(
            project_id=project_id,
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
        repository: DefinitionRepository,
        project_id: str,
        instruction_type: DefinitionType,
    ) -> tuple[ExecutionInstruction, ...]:
        summaries = await repository.list_available_for_workspace(
            project_id=project_id,
            instruction_type=instruction_type,
        )
        documents: list[AvailableDefinitionDocument] = []

        for summary in summaries:
            if not summary.selectable:
                continue

            document = await (
                repository.get_available_for_workspace(
                    project_id=project_id,
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
        document: AvailableDefinitionDocument,
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
