"""In-memory validation lookup adapter for tests."""

from src.app.services.shared.validation_service import ValidationService

from .instruction_repository import FakeInstructionRepository


class FakeValidationRepository:
    """Validation repository backed by the in-memory resource stores."""

    def __init__(
        self,
        *,
        instruction_repository: FakeInstructionRepository | None = None,
    ) -> None:
        self._instruction_repository = instruction_repository

    async def find_resource_id_by_name(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        normalized_name: str,
    ) -> str | None:
        for resource_id, resource_workspace, current_type, name in (
            self._iter_resources()
        ):
            if resource_workspace != workspace_id:
                continue

            if current_type != resource_type:
                continue

            if ValidationService.normalize_name(name) == normalized_name:
                return resource_id

        return None

    def _iter_resources(
        self,
    ) -> list[tuple[str, str, str, str]]:
        resources: list[tuple[str, str, str, str]] = []

        if self._instruction_repository is not None:
            resources.extend(
                (
                    document.id,
                    document.workspace_id,
                    document.instruction_type,
                    document.name,
                )
                for document in self._instruction_repository.documents
            )

        return resources
