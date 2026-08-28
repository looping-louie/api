from copy import deepcopy
from dataclasses import replace
from typing import Sequence

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.catalogs.persona_skills import (
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)
from src.app.services.persona_skills import (
    AvailableDefinitionDocument,
    AvailableDefinitionPage,
    AvailableDefinitionSummary,
    DefinitionDocument,
    DefinitionSummary,
    DefinitionType,
)


class FakeInstructionRepository:
    """In-memory instruction repository used by service tests."""

    def __init__(self) -> None:
        self._documents: dict[
            tuple[str, DefinitionType, str],
            DefinitionDocument,
        ] = {}
        self._available_documents: dict[
            tuple[DefinitionType, str],
            AvailableDefinitionDocument,
        ] = {}
        self._enabled_settings: dict[
            tuple[str, str],
            bool,
        ] = {}

    @property
    def documents(self) -> list[DefinitionDocument]:
        """Return copies of every stored document."""

        return [
            deepcopy(document)
            for document in self._documents.values()
        ]

    def seed(self, document: DefinitionDocument) -> None:
        """Insert a document directly into the fake repository."""

        key = self._build_key(
            project_id=document.project_id,
            instruction_type=document.instruction_type,
            instruction_id=document.id,
        )
        self._documents[key] = deepcopy(document)

    def seed_available(
        self,
        document: AvailableDefinitionDocument,
    ) -> None:
        """Insert a global or marketplace definition for service tests."""

        self._available_documents[
            (
                document.instruction_type,
                document.id,
            )
        ] = deepcopy(document)

    async def list_summaries(
        self,
        *,
        project_id: str,
        instruction_type: DefinitionType,
        search: str | None = None,
    ) -> Sequence[DefinitionSummary]:
        documents = [
            document
            for document in self._documents.values()
            if document.project_id == project_id
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
            DefinitionSummary(
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
        project_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
    ) -> DefinitionDocument | None:
        key = self._build_key(
            project_id=project_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )
        document = self._documents.get(key)

        if document is None:
            return None

        return deepcopy(document)

    async def list_available_for_workspace(
        self,
        *,
        project_id: str,
        instruction_type: DefinitionType,
        search: str | None = None,
        include_deprecated: bool = False,
        status: CatalogInstructionStatus | None = None,
        categories: Sequence[CatalogInstructionCategory] = (),
        sort: CatalogInstructionSort | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> AvailableDefinitionPage:
        """Return a filtered catalog page matching SQLite persistence."""

        documents = self._available_for_workspace(
            project_id=project_id,
            instruction_type=instruction_type,
            include_deprecated=include_deprecated,
        )

        if search is not None:
            comparison = " ".join(
                search.strip().casefold().split()
            )
            documents = [
                document
                for document in documents
                if comparison in document.name.casefold()
                or comparison in document.description.casefold()
            ]

        if status is not None:
            enabled = status == CatalogInstructionStatus.ENABLED
            documents = [
                document
                for document in documents
                if document.enabled is enabled
            ]

        if categories:
            category_values = {category.value for category in categories}
            documents = [
                document
                for document in documents
                if document.metadata.get("category") in category_values
            ]

        if sort == CatalogInstructionSort.ALPHABETICAL_DESC:
            documents.sort(
                key=self._available_sort_key,
                reverse=True,
            )
        elif sort == CatalogInstructionSort.NEWEST:
            documents.sort(
                key=lambda document: (
                    -document.created_at.timestamp(),
                    *self._available_sort_key(document),
                )
            )
        elif sort == CatalogInstructionSort.OLDEST:
            documents.sort(
                key=lambda document: (
                    document.created_at,
                    *self._available_sort_key(document),
                )
            )
        else:
            documents.sort(key=self._available_sort_key)

        summaries = tuple(
            AvailableDefinitionSummary(
                id=document.id,
                project_id=document.project_id,
                instruction_type=document.instruction_type,
                origin=document.origin,
                owner_project_id=document.owner_project_id,
                source_instruction_id=document.source_instruction_id,
                name=document.name,
                description=document.description,
                enabled=document.enabled,
                enabled_by_default=document.enabled_by_default,
                deprecated=document.deprecated,
                catalog_version=document.catalog_version,
                version=document.version,
                created_at=document.created_at,
                updated_at=document.updated_at,
                category=(
                    str(document.metadata["category"])
                    if document.metadata.get("category") is not None
                    else None
                ),
            )
            for document in documents
        )
        page_items = (
            summaries[offset : offset + limit]
            if limit is not None
            else summaries[offset:]
        )
        return AvailableDefinitionPage(
            items=page_items,
            total=len(summaries),
        )

    @staticmethod
    def _available_sort_key(
        document: AvailableDefinitionDocument,
    ) -> tuple[str, str, str]:
        """Return the deterministic alphabetical catalog sort key."""

        return (
            " ".join(document.name.strip().casefold().split()),
            document.name.casefold(),
            document.id,
        )

    async def get_available_for_workspace(
        self,
        *,
        project_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
        include_deprecated: bool = False,
    ) -> AvailableDefinitionDocument | None:
        matches = [
            document
            for document in self._available_for_workspace(
                project_id=project_id,
                instruction_type=instruction_type,
                include_deprecated=include_deprecated,
            )
            if document.id == instruction_id
        ]

        if not matches:
            return None

        return deepcopy(matches[0])

    async def get_owned_custom(
        self,
        *,
        project_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
    ) -> DefinitionDocument | None:
        return await self.get(
            project_id=project_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

    async def set_enabled(
        self,
        *,
        project_id: str,
        instruction_id: str,
        enabled: bool,
    ) -> bool:
        visible = [
            document
            for instruction_type in ("persona", "skill")
            for document in self._available_for_workspace(
                project_id=project_id,
                instruction_type=instruction_type,
                include_deprecated=False,
            )
            if document.id == instruction_id
        ]

        if not visible:
            return False

        self._enabled_settings[
            (
                project_id,
                instruction_id,
            )
        ] = enabled
        return True

    async def is_enabled(
        self,
        *,
        project_id: str,
        instruction_id: str,
    ) -> bool:
        for instruction_type in ("persona", "skill"):
            document = await self.get_available_for_workspace(
                project_id=project_id,
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

            if document is not None:
                return document.selectable

        return False

    async def create(
        self,
        *,
        document: DefinitionDocument,
    ) -> DefinitionDocument:
        key = self._build_key(
            project_id=document.project_id,
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
        document: DefinitionDocument,
        expected_version: int,
    ) -> DefinitionDocument | None:
        key = self._build_key(
            project_id=document.project_id,
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
        project_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
    ) -> bool:
        key = self._build_key(
            project_id=project_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if key not in self._documents:
            return False

        del self._documents[key]
        return True

    def _available_for_workspace(
        self,
        *,
        project_id: str,
        instruction_type: DefinitionType,
        include_deprecated: bool,
    ) -> list[AvailableDefinitionDocument]:
        documents = [
            self._custom_to_available(
                document,
                project_id=project_id,
            )
            for document in self._documents.values()
            if (
                document.project_id == project_id
                and document.instruction_type == instruction_type
            )
        ]

        for document in self._available_documents.values():
            if document.instruction_type != instruction_type:
                continue

            setting_key = (
                project_id,
                document.id,
            )
            visible = (
                document.origin == InstructionOrigin.BUILTIN
                or (
                    document.origin == InstructionOrigin.CUSTOM
                    and document.owner_project_id == project_id
                )
                or (
                    document.origin == InstructionOrigin.MARKETPLACE
                    and setting_key in self._enabled_settings
                )
            )

            if not visible:
                continue

            documents.append(
                replace(
                    deepcopy(document),
                    project_id=project_id,
                    enabled=self._enabled_settings.get(
                        setting_key,
                        document.enabled_by_default,
                    ),
                )
            )

        if not include_deprecated:
            documents = [
                document
                for document in documents
                if not document.deprecated
            ]

        return documents

    def _custom_to_available(
        self,
        document: DefinitionDocument,
        *,
        project_id: str,
    ) -> AvailableDefinitionDocument:
        enabled_by_default = True
        enabled = self._enabled_settings.get(
            (
                project_id,
                document.id,
            ),
            enabled_by_default,
        )
        return AvailableDefinitionDocument(
            id=document.id,
            project_id=project_id,
            instruction_type=document.instruction_type,
            origin=InstructionOrigin.CUSTOM,
            owner_project_id=document.project_id,
            source_instruction_id=document.source_instruction_id,
            name=document.name,
            description=document.description,
            instructions=document.instructions,
            metadata=deepcopy(dict(document.metadata)),
            enabled=enabled,
            enabled_by_default=enabled_by_default,
            deprecated=False,
            catalog_version=None,
            checksum=None,
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @staticmethod
    def _build_key(
        *,
        project_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
    ) -> tuple[str, DefinitionType, str]:
        return project_id, instruction_type, instruction_id
