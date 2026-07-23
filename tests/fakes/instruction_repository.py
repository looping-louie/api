from copy import deepcopy
from dataclasses import replace
from typing import Sequence

from src.app.catalogs.instructions import InstructionOrigin
from src.app.services.shared.instruction_service import (
    AvailableInstructionDocument,
    AvailableInstructionSummary,
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
        self._available_documents: dict[
            tuple[InstructionType, str],
            AvailableInstructionDocument,
        ] = {}
        self._enabled_settings: dict[
            tuple[str, str],
            bool,
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

    def seed_available(
        self,
        document: AvailableInstructionDocument,
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

    async def list_available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
        include_deprecated: bool = False,
    ) -> Sequence[AvailableInstructionSummary]:
        documents = self._available_for_workspace(
            workspace_id=workspace_id,
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

        documents.sort(
            key=lambda document: (
                " ".join(
                    document.name.strip().casefold().split()
                ),
                document.name.casefold(),
                document.id,
            )
        )
        return [
            AvailableInstructionSummary(
                id=document.id,
                workspace_id=document.workspace_id,
                instruction_type=document.instruction_type,
                origin=document.origin,
                owner_workspace_id=document.owner_workspace_id,
                name=document.name,
                description=document.description,
                enabled=document.enabled,
                enabled_by_default=document.enabled_by_default,
                deprecated=document.deprecated,
                catalog_version=document.catalog_version,
                version=document.version,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
            for document in documents
        ]

    async def get_available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        include_deprecated: bool = False,
    ) -> AvailableInstructionDocument | None:
        matches = [
            document
            for document in self._available_for_workspace(
                workspace_id=workspace_id,
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
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument | None:
        return await self.get(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

    async def set_enabled(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
        enabled: bool,
    ) -> bool:
        visible = [
            document
            for instruction_type in ("persona", "skill")
            for document in self._available_for_workspace(
                workspace_id=workspace_id,
                instruction_type=instruction_type,
                include_deprecated=False,
            )
            if document.id == instruction_id
        ]

        if not visible:
            return False

        self._enabled_settings[
            (
                workspace_id,
                instruction_id,
            )
        ] = enabled
        return True

    async def is_enabled(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
    ) -> bool:
        for instruction_type in ("persona", "skill"):
            document = await self.get_available_for_workspace(
                workspace_id=workspace_id,
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

            if document is not None:
                return document.selectable

        return False

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

    def _available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        include_deprecated: bool,
    ) -> list[AvailableInstructionDocument]:
        documents = [
            self._custom_to_available(
                document,
                workspace_id=workspace_id,
            )
            for document in self._documents.values()
            if (
                document.workspace_id == workspace_id
                and document.instruction_type == instruction_type
            )
        ]

        for document in self._available_documents.values():
            if document.instruction_type != instruction_type:
                continue

            setting_key = (
                workspace_id,
                document.id,
            )
            visible = (
                document.origin == InstructionOrigin.BUILTIN
                or (
                    document.origin == InstructionOrigin.CUSTOM
                    and document.owner_workspace_id == workspace_id
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
                    workspace_id=workspace_id,
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
        document: InstructionDocument,
        *,
        workspace_id: str,
    ) -> AvailableInstructionDocument:
        enabled_by_default = True
        enabled = self._enabled_settings.get(
            (
                workspace_id,
                document.id,
            ),
            enabled_by_default,
        )
        return AvailableInstructionDocument(
            id=document.id,
            workspace_id=workspace_id,
            instruction_type=document.instruction_type,
            origin=InstructionOrigin.CUSTOM,
            owner_workspace_id=document.workspace_id,
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
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> tuple[str, InstructionType, str]:
        return workspace_id, instruction_type, instruction_id
