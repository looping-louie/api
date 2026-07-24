"""Controller for pipeline HTTP operations."""

from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.schemas.pipeline import (
    PipelineChangelogEntryResponse,
    PipelineChangelogListResponse,
    PipelineCreateRequest,
    PipelineHumanGateStepRequest,
    PipelineListResponse,
    PipelineLoopStepRequest,
    PipelinePatchRequest,
    PipelineResponse,
    PipelineStepRequest,
)
from src.app.services.pipeline_service import PipelineService
from src.app.services.pipeline_types import (
    PipelineCreate,
    PipelinePatch,
    PipelineQuizConfigInput,
    PipelineStepInput,
)


class PipelineController:
    """Translate pipeline HTTP schemas to and from application values."""

    def __init__(self, *, pipeline_service: PipelineService) -> None:
        """Store the pipeline application service."""

        self._pipeline_service = pipeline_service

    async def list(
        self,
        *,
        user_id: str,
        offset: int,
        status: str | None,
        search: str | None,
        requested_workspace_id: str | None = None,
    ) -> PipelineListResponse:
        """Return one filtered pipeline page."""

        documents, total = await self._pipeline_service.list(
            user_id=user_id,
            offset=offset,
            status=status,
            search=search,
            requested_workspace_id=requested_workspace_id,
        )
        return PipelineListResponse(
            items=[
                PipelineResponse.model_validate(document)
                for document in documents
            ],
            total=total,
        )

    async def get(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        requested_workspace_id: str | None = None,
    ) -> PipelineResponse:
        """Return one complete pipeline."""

        document = await self._pipeline_service.get(
            user_id=user_id,
            pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
        )
        return PipelineResponse.model_validate(document)

    async def create(
        self,
        *,
        user_id: str,
        payload: PipelineCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> PipelineResponse:
        """Create one enabled pipeline."""

        document = await self._pipeline_service.create(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            payload=PipelineCreate(
                title=payload.title,
                description=payload.description,
                steps=self._steps(payload.steps),
            ),
        )
        return PipelineResponse.model_validate(document)

    async def patch(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        payload: PipelinePatchRequest,
        requested_workspace_id: str | None = None,
    ) -> PipelineResponse:
        """Apply supplied mutable pipeline fields."""

        document = await self._pipeline_service.patch(
            user_id=user_id,
            pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
            payload=PipelinePatch(
                provided_fields=frozenset(payload.model_fields_set),
                title=payload.title,
                description=payload.description,
                enabled=payload.enabled,
                steps=(
                    self._steps(payload.steps)
                    if payload.steps is not None
                    else None
                ),
            ),
        )
        return PipelineResponse.model_validate(document)

    async def delete(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        """Archive one pipeline definition."""

        await self._pipeline_service.archive(
            user_id=user_id,
            pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
        )
        return DeleteResponse()

    async def list_changelog(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> PipelineChangelogListResponse:
        """Return one newest-first pipeline changelog page."""

        entries, total = await self._pipeline_service.list_changelog(
            user_id=user_id,
            pipeline_id=pipeline_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return PipelineChangelogListResponse(
            items=[
                PipelineChangelogEntryResponse.model_validate(entry)
                for entry in entries
            ],
            total=total,
        )

    @classmethod
    def _steps(
        cls,
        values: list[PipelineStepRequest],
    ) -> tuple[PipelineStepInput, ...]:
        """Translate already-validated discriminated step schemas."""

        return tuple(cls._step(value) for value in values)

    @staticmethod
    def _step(value: PipelineStepRequest) -> PipelineStepInput:
        """Translate one request step without applying business rules."""

        if isinstance(value, PipelineLoopStepRequest):
            return PipelineStepInput(
                type=value.type,
                loop_id=value.loop_id,
            )
        assert isinstance(value, PipelineHumanGateStepRequest)
        config = value.config
        return PipelineStepInput(
            type=value.type,
            gate_type=value.gate_type,
            config=(
                PipelineQuizConfigInput(
                    minimum_correct_answers=(
                        config.minimum_correct_answers
                    ),
                    question_count=config.question_count,
                    option_count=config.option_count,
                )
                if config is not None
                else None
            ),
        )
