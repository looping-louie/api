"""Build append-only observability events for Pipeline execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline_run import (
    PipelineRunDocument,
    PipelineRunEventDocument,
)


class PipelineRunEventBuilder:
    """Create normalized scheduler and Harness events with stable ownership."""

    def __init__(self, id_factory: Callable[[], str]) -> None:
        """Store the identifier source shared with Pipeline runs."""

        self._id_factory = id_factory

    def created(
        self,
        *,
        project_id: str,
        run_id: str,
        actor_id: str,
        commit_mode: str,
        created_at: datetime,
    ) -> PipelineRunEventDocument:
        """Record creation of one immutable PipelineRun snapshot."""

        return self._event(
            project_id=project_id,
            run_id=run_id,
            event_type='pipeline_run_created',
            activity_id=None,
            actor_id=actor_id,
            payload={'commit_mode': commit_mode},
            created_at=created_at,
        )

    def claimed(
        self,
        *,
        document: PipelineRunDocument,
        child: ActivityRunDocument,
        worker_id: str,
        created_at: datetime,
        step_started: bool,
    ) -> tuple[PipelineRunEventDocument, ...]:
        """Record worker ownership and a newly materialized first step."""

        events = [self._event(
            project_id=document.project_id,
            run_id=document.id,
            event_type='pipeline_run_claimed',
            activity_id=child.activity_id,
            actor_id=worker_id,
            payload={
                'worker_id': worker_id,
                'attempt': document.attempt,
                'activity_run_id': child.id,
                'lease_expires_at': (
                    document.lease_expires_at.isoformat()
                    if document.lease_expires_at is not None
                    else None
                ),
            },
            created_at=created_at,
        )]
        if step_started:
            events.append(self._step_started(
                document=document,
                child=child,
                actor_id=worker_id,
                created_at=created_at,
            ))
        return tuple(events)

    def started_child(
        self,
        *,
        document: PipelineRunDocument,
        child: ActivityRunDocument,
        actor_id: str,
        created_at: datetime,
    ) -> tuple[PipelineRunEventDocument, ...]:
        """Record a human child materialized without a worker claim."""

        return (self._step_started(
            document=document,
            child=child,
            actor_id=actor_id,
            created_at=created_at,
        ),)

    def finished_child(
        self,
        *,
        document: PipelineRunDocument,
        child: ActivityRunDocument,
        actor_id: str,
        created_at: datetime,
        next_child: ActivityRunDocument | None,
    ) -> tuple[PipelineRunEventDocument, ...]:
        """Record Harness output, terminal step state, and its successor start."""

        events: list[PipelineRunEventDocument] = []
        artifacts = child.execution_context.get('runtime_artifacts')
        if isinstance(artifacts, Mapping) and self._is_harness_observation(
            artifacts
        ):
            payload = {'activity_run_id': child.id, **dict(artifacts)}
            events.append(self._event(
                project_id=document.project_id,
                run_id=document.id,
                event_type=(
                    'harness_turn_completed'
                    if artifacts.get('completed') is True
                    else 'harness_turn_failed'
                ),
                activity_id=child.activity_id,
                actor_id=actor_id,
                payload=payload,
                created_at=created_at,
            ))
        step_status = 'completed' if child.status == 'completed' else 'failed'
        events.append(self._event(
            project_id=document.project_id,
            run_id=document.id,
            event_type=f'pipeline_step_{step_status}',
            activity_id=child.activity_id,
            actor_id=actor_id,
            payload={
                'activity_run_id': child.id,
                'status': step_status,
                'started_at': child.created_at.isoformat(),
                'completed_at': child.updated_at.isoformat(),
            },
            created_at=created_at,
        ))
        if next_child is not None:
            events.append(self._step_started(
                document=document,
                child=next_child,
                actor_id=actor_id,
                created_at=created_at,
            ))
        return tuple(events)

    def _step_started(
        self,
        *,
        document: PipelineRunDocument,
        child: ActivityRunDocument,
        actor_id: str,
        created_at: datetime,
    ) -> PipelineRunEventDocument:
        """Build one step-start event for a persisted ActivityRun child."""

        step = next(
            item for item in document.steps if item.activity_id == child.activity_id
        )
        harness = child.activity_snapshot.get('harness')
        return self._event(
            project_id=document.project_id,
            run_id=document.id,
            event_type='pipeline_step_started',
            activity_id=child.activity_id,
            actor_id=actor_id,
            payload={
                'activity_run_id': child.id,
                'position': step.position,
                'harness': dict(harness) if isinstance(harness, Mapping) else None,
            },
            created_at=created_at,
        )

    def _event(
        self,
        *,
        project_id: str,
        run_id: str,
        event_type: str,
        activity_id: str | None,
        actor_id: str,
        payload: Mapping[str, object],
        created_at: datetime,
    ) -> PipelineRunEventDocument:
        """Build one immutable event for an atomic repository transition."""

        return PipelineRunEventDocument(
            id=self._id_factory(),
            project_id=project_id,
            pipeline_run_id=run_id,
            event_type=event_type,
            activity_id=activity_id,
            actor_id=actor_id,
            payload=dict(payload),
            created_at=created_at,
        )

    @staticmethod
    def _is_harness_observation(artifacts: Mapping[str, object]) -> bool:
        """Return whether runtime artifacts use the common Harness envelope."""

        return (
            isinstance(artifacts.get('schema_version'), str)
            and isinstance(artifacts.get('harness'), Mapping)
            and isinstance(artifacts.get('completed'), bool)
        )
