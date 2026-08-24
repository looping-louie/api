"""Persona and skill definition lifecycle services."""

from __future__ import annotations

from .lifecycle import _DefinitionLifecycleService
from .types import Clock, IdFactory, InstructionRepository
from ..shared.dependency_checker import DependencyChecker
from ..shared.validation import ValidationService


class PersonaDefinitionService(_DefinitionLifecycleService):
    """Lifecycle service for persona definitions."""

    def __init__(
        self,
        *,
        repository: InstructionRepository,
        validation_service: ValidationService,
        dependency_checker: DependencyChecker,
        id_factory: IdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize persistence lifecycle behavior for personas."""

        super().__init__(
            repository=repository,
            validation_service=validation_service,
            dependency_checker=dependency_checker,
            instruction_type="persona",
            id_factory=id_factory,
            clock=clock,
        )


class SkillDefinitionService(_DefinitionLifecycleService):
    """Lifecycle service for skill definitions."""

    def __init__(
        self,
        *,
        repository: InstructionRepository,
        validation_service: ValidationService,
        dependency_checker: DependencyChecker,
        id_factory: IdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize persistence lifecycle behavior for skills."""

        super().__init__(
            repository=repository,
            validation_service=validation_service,
            dependency_checker=dependency_checker,
            instruction_type="skill",
            id_factory=id_factory,
            clock=clock,
        )
