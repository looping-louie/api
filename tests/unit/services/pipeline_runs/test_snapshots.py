"""Behavior tests for immutable PipelineRun execution snapshots."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.app.models.pipeline import (
    PipelineActivityStep,
    PipelineDetails,
    PipelineDocument,
    PipelineHarness,
)
from src.app.models.user import UserDocument, UserSettings
from src.app.services.pipeline_runs.service import PipelineRunService
from src.app.services.shared.tenant import TenantService
from tests.conftest import IncrementingClock
from tests.unit.services.pipeline_runs.test_service import (
    InMemoryActivityRunRepository,
    InMemoryPipelineRunRepository,
    PipelineDetailsService,
    activity,
)


class StaticUserService:
    """Return one user with fixed execution defaults."""

    def __init__(self, document: UserDocument) -> None:
        """Store the user returned by every lookup."""

        self._document = document

    async def get(self, **_: object) -> UserDocument:
        """Return the configured current user."""

        return self._document


class StaticModelExecutionService:
    """Select one deterministic linked service for Louie snapshots."""

    async def select_linked_service(
        self,
        *,
        user_id: str,
        **_: object,
    ) -> SimpleNamespace:
        """Return the service selected by this scheduler fixture."""

        return SimpleNamespace(id='linked-service-selected', user_id=user_id)


class StaticInstructionLibrary:
    """Return immutable Persona and Skill values for a Codex Activity."""

    def agent_snapshot(self, persona_id: str) -> dict[str, object]:
        """Return a deterministic snapshot for the selected Persona."""

        return {
            'snapshot_version': 1,
            'persona': {
                'id': persona_id,
                'instruction_type': 'persona',
                'version': 2,
                'name': 'Implementer',
                'description': 'Implements focused changes.',
                'content': 'Implement the requested change carefully.',
            },
            'skills': [
                {
                    'id': 'skill-api',
                    'instruction_type': 'skill',
                    'version': 3,
                    'name': 'API Compatibility',
                    'description': 'Preserve existing API contracts.',
                    'content': 'Keep public API contracts backwards compatible.',
                },
            ],
        }


class StaticInstructionLibraryService:
    """Load one deterministic instruction library per PipelineRun."""

    def __init__(self) -> None:
        """Initialize recorded tenant lookups."""

        self.calls: list[tuple[str, str | None]] = []

    async def load(
        self,
        *,
        user_id: str,
        requested_project_id: str | None = None,
    ) -> StaticInstructionLibrary:
        """Return the configured library and record its user and Project."""

        self.calls.append((user_id, requested_project_id))
        return StaticInstructionLibrary()


@pytest.mark.asyncio
async def test_create_freezes_codex_persona_skills_and_execution_defaults(
    tenant_service: TenantService,
) -> None:
    """Codex instructions and narrower execution values are frozen at creation."""

    now = datetime(2026, 8, 25, tzinfo=UTC)
    first = replace(
        activity('activity-1'),
        model_id='model-activity',
        harness=PipelineHarness(kind='codex_cli'),
        config={
            **activity('activity-1').config,
            'agents': [{
                'model_id': 'model-agent',
                'persona_id': 'persona-1',
                'role': 'generator',
            }],
        },
    )
    second = replace(
        activity('activity-2'),
        config={
            **activity('activity-2').config,
            'agents': [{'persona_id': 'persona-2', 'role': 'generator'}],
        },
    )
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', name='Pipeline',
            description='Run configured steps.', status='active',
            steps=(
                PipelineActivityStep(activity_id=first.id),
                PipelineActivityStep(activity_id=second.id),
            ),
            model_id='model-pipeline', harness=PipelineHarness(kind='louie'),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(first, second),
    )
    runs = InMemoryPipelineRunRepository()
    instruction_service = StaticInstructionLibraryService()
    service = PipelineRunService(
        repository=runs,
        activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details),
        tenant_service=tenant_service,
        model_execution_service=StaticModelExecutionService(),  # type: ignore[arg-type]
        instruction_library_service=instruction_service,  # type: ignore[arg-type]
        id_factory=lambda: 'run-1', clock=IncrementingClock(),
    )

    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )

    first_snapshot = created.steps[0].activity_snapshot
    first_agent = first_snapshot['agents'][0]
    second_agent = created.steps[1].activity_snapshot['agents'][0]
    assert created.pipeline_snapshot['harness']['kind'] == 'louie'
    assert first_snapshot['harness']['kind'] == 'codex_cli'
    assert first_agent['model_id'] == 'model-agent'
    assert first_snapshot['instruction_snapshot']['persona']['id'] == 'persona-1'
    assert first_snapshot['instruction_snapshot']['persona']['version'] == 2
    assert first_snapshot['instruction_snapshot']['skills'][0]['id'] == 'skill-api'
    assert 'instruction_snapshot' not in created.steps[1].activity_snapshot
    assert second_agent['model_target'] == {
        'linked_service_id': 'linked-service-selected',
        'linked_service_user_id': 'user-1',
        'model_id': 'model-pipeline',
    }
    assert instruction_service.calls == [('user-1', 'workspace-1')]


@pytest.mark.asyncio
async def test_create_freezes_user_execution_defaults_when_unset(
    tenant_service: TenantService,
) -> None:
    """User candidates supply otherwise unset Pipeline and Activity values."""

    now = datetime(2026, 8, 25, tzinfo=UTC)
    configured_activity = replace(
        activity('activity-1'),
        config={
            **activity('activity-1').config,
            'agents': [{'persona_id': 'persona-1', 'role': 'generator'}],
        },
    )
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', name='Pipeline',
            description='Run configured steps.', status='active',
            steps=(PipelineActivityStep(activity_id=configured_activity.id),),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(configured_activity,),
    )
    runs = InMemoryPipelineRunRepository()
    service = PipelineRunService(
        repository=runs,
        activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details),
        tenant_service=tenant_service,
        user_service=StaticUserService(UserDocument(  # type: ignore[arg-type]
            id='user-1', created_at=now, updated_at=now,
            settings=UserSettings(
                default_model_id='model-user',
                default_harness=PipelineHarness(kind='codex_cli'),
            ),
        )),
        instruction_library_service=StaticInstructionLibraryService(),  # type: ignore[arg-type]
        id_factory=lambda: 'run-1', clock=IncrementingClock(),
    )

    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )

    assert created.pipeline_snapshot['harness']['kind'] == 'codex_cli'
    assert created.steps[0].activity_snapshot['harness']['kind'] == 'codex_cli'
    assert 'model_id' not in created.steps[0].activity_snapshot['agents'][0]
    assert created.steps[0].activity_snapshot['instruction_snapshot']['persona'][
        'id'
    ] == 'persona-1'
