from copy import deepcopy
from typing import Sequence

from src.app.services.shared.composition_service import (
    CompositionDocument,
    CompositionSummary,
    CompositionType,
)


class FakeCompositionRepository:
    """In-memory composition repository used by service tests."""

    def __init__(self) -> None:
        self._documents: dict[
            tuple[str, CompositionType, str],
            CompositionDocument,
        ] = {}

    @property
    def documents(self) -> list[CompositionDocument]:
        """Return copies of every stored composition."""

        return [
            deepcopy(document)
            for document in self._documents.values()
        ]

    def seed(self, document: CompositionDocument) -> None:
        """Insert a composition directly into the repository."""

        key = self._build_key(
            workspace_id=document.workspace_id,
            composition_type=document.composition_type,
            composition_id=document.id,
        )
        self._documents[key] = deepcopy(document)

    async def list_summaries(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        search: str | None = None,
    ) -> Sequence[CompositionSummary]:
        documents = [
            document
            for document in self._documents.values()
            if document.workspace_id == workspace_id
            and document.composition_type == composition_type
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
            CompositionSummary(
                id=document.id,
                name=document.name,
                description=document.description,
                version=document.version,
                item_count=len(document.items),
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
            for document in documents
        ]

    async def get(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> CompositionDocument | None:
        key = self._build_key(
            workspace_id=workspace_id,
            composition_type=composition_type,
            composition_id=composition_id,
        )
        document = self._documents.get(key)

        if document is None:
            return None

        return deepcopy(document)

    async def create(
        self,
        *,
        document: CompositionDocument,
    ) -> CompositionDocument:
        key = self._build_key(
            workspace_id=document.workspace_id,
            composition_type=document.composition_type,
            composition_id=document.id,
        )

        if key in self._documents:
            raise AssertionError(
                f"Composition already exists: {document.id}"
            )

        self._documents[key] = deepcopy(document)
        return deepcopy(document)

    async def update(
        self,
        *,
        document: CompositionDocument,
        expected_version: int,
    ) -> CompositionDocument | None:
        key = self._build_key(
            workspace_id=document.workspace_id,
            composition_type=document.composition_type,
            composition_id=document.id,
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
        composition_type: CompositionType,
        composition_id: str,
    ) -> bool:
        key = self._build_key(
            workspace_id=workspace_id,
            composition_type=composition_type,
            composition_id=composition_id,
        )

        if key not in self._documents:
            return False

        del self._documents[key]
        return True

    @staticmethod
    def _build_key(
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> tuple[str, CompositionType, str]:
        return workspace_id, composition_type, composition_id
