"""Supporting operations shared across pipeline service use cases."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable

from src.app.models.changelog import JsonObject
from src.app.models.pipeline import (
    PipelineChangelogEntry,
    PipelineDocument,
    PipelineLoopStep,
    PipelineStatus,
)
from src.app.repositories.loops.loop_repository import LoopRepository
from src.app.repositories.pipelines.pipeline_repository import (
    PipelineRepository,
)
from src.app.services.loop_types import LoopNotFoundError
from src.app.services.pipeline_types import (
    InvalidPipelineStepsError,
    PipelineNotFoundError,
)
from src.app.services.pipeline_validation import require_text
from src.app.services.shared.changelog import build_changelog_metadata
from src.app.services.shared.pagination import require_offset


async def validate_loop_references(
    loop_repository: LoopRepository,
    document: PipelineDocument,
) -> None:
    """Require every unique referenced loop to exist and be active."""

    loop_ids = tuple(
        dict.fromkeys(
            step.loop_id
            for step in document.steps
            if isinstance(step, PipelineLoopStep)
        )
    )
    loops = await asyncio.gather(
        *(
            loop_repository.get(
                workspace_id=document.workspace_id,
                loop_id=loop_id,
            )
            for loop_id in loop_ids
        )
    )
    for loop_id, loop in zip(loop_ids, loops):
        if loop is None or loop.status != "active":
            raise LoopNotFoundError(loop_id=loop_id)


async def require_pipeline(
    repository: PipelineRepository,
    *,
    workspace_id: str,
    pipeline_id: str,
) -> PipelineDocument:
    """Load one pipeline or raise its stable not-found error."""

    normalized_id = require_text(pipeline_id, "pipeline_id")
    document = await repository.get(
        workspace_id=workspace_id,
        pipeline_id=normalized_id,
    )
    if document is None:
        raise PipelineNotFoundError(pipeline_id=normalized_id)
    return document


def build_entry(
    *,
    id_factory: Callable[[], str],
    document: PipelineDocument,
    actor_id: str,
    change_type: str,
    changed_at: datetime,
    diff: JsonObject | None = None,
    content: JsonObject | None = None,
) -> PipelineChangelogEntry:
    """Build one generated pipeline changelog entry."""

    metadata = build_changelog_metadata(
        entry_id=id_factory(),
        workspace_id=document.workspace_id,
        actor_id=actor_id,
        changed_at=changed_at,
        diff=diff,
        content=content,
    )
    return PipelineChangelogEntry(
        id=metadata.id,
        pipeline_id=document.id,
        workspace_id=metadata.workspace_id,
        change_type=change_type,  # type: ignore[arg-type]
        actor_id=metadata.actor_id,
        changed_at=metadata.changed_at,
        diff=metadata.diff,
        content=metadata.content,
    )


def change_type(before: PipelineStatus, after: PipelineStatus) -> str:
    """Select an enablement event or an ordinary update."""

    if before == after:
        return "updated"
    return "enabled" if after == "active" else "disabled"


def normalize_offset(value: object) -> int:
    """Translate shared offset validation to the pipeline contract."""

    try:
        return require_offset(value)
    except ValueError as error:
        raise InvalidPipelineStepsError(
            field_name="offset",
            message="must be a non-negative integer",
        ) from error


def normalize_search(value: object) -> str | None:
    """Normalize an optional one-to-200-character search term."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidPipelineStepsError(
            field_name="search",
            message="must be a string",
        )
    normalized = value.strip()
    if not 1 <= len(normalized) <= 200:
        raise InvalidPipelineStepsError(
            field_name="search",
            message="must contain between 1 and 200 characters",
        )
    return normalized
