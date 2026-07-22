from copy import deepcopy
from typing import Sequence

from src.app.services.shared.instruction_service import (
    InstructionDocument,
    InstructionSummary,
    InstructionType,
)


class FakeInstructionRepository:
    """In-memory instruction repository used by service tests."""

    def __init__(self) -> None:
        self._documents: dict[
            tuple[str, InstructionType, str],
            InstructionDocument,
        ] = {}

    @property
    def documents(self) -> list[InstructionDocument]:
        """Return copies of every stored document."""

        return [
            deepcopy(document)
            for document in self._documents.values()
        ]

    def seed(self, document: InstructionDocument) -> None:
        """Insert a document directly into the fake repository."""

        key = self._build_key(
            workspace_id=document.workspace_id,
            instruction_type=document.instruction_type,
            instruction_id=document.id,
        )
        self._documents[key] = deepcopy(document)

    async def list_summaries(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
    ) -> Sequence[InstructionSummary]:
        documents = [
            document
            for document in self._documents.values()
            if document.workspace_id == workspace_id
            and document.instruction_type == instruction_type
        ]

        if search is not None:
            comparison = search.casefold()
            documents = [
                document
                for document in documents
                if comparison in document.name.casefold()
                or comparison in document.description.casefold()
            ]

        documents.sort(key=lambda document: document.name.casefold())

        return [
            InstructionSummary(
                id=document.id,
                name=document.name,
                description=document.description,
                version=document.version,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
            for document in documents
        ]

    async def get(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument | None:
        key = self._build_key(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )
        document = self._documents.get(key)

        if document is None:
            return None

        return deepcopy(document)

    async def create(
        self,
        *,
        document: InstructionDocument,
    ) -> InstructionDocument:
        key = self._build_key(
            workspace_id=document.workspace_id,
            instruction_type=document.instruction_type,
            instruction_id=document.id,
        )

        if key in self._documents:
            raise AssertionError(f"Instruction already exists: {document.id}")

        self._documents[key] = deepcopy(document)
        return deepcopy(document)

    async def update(
        self,
        *,
        document: InstructionDocument,
        expected_version: int,
    ) -> InstructionDocument | None:
        key = self._build_key(
            workspace_id=document.workspace_id,
            instruction_type=document.instruction_type,
            instruction_id=document.id,
        )
        current = self._documents.get(key)

        if current is None or current.version != expected_version:
            return None

        self._documents[key] = deepcopy(document)
        return deepcopy(document)

    async def delete(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> bool:
        key = self._build_key(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if key not in self._documents:
            return False

        del self._documents[key]
        return True

    @staticmethod
    def _build_key(
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> tuple[str, InstructionType, str]:
        return workspace_id, instruction_type, instruction_id
