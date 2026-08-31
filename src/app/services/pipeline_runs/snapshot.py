"""Build immutable Pipeline and Activity execution snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy

from src.app.models.activity import ActivityDocument
from src.app.models.pipeline import PipelineDetails, PipelineHarness
from src.app.services.execution_instructions import (
    ExecutionInstructionLibrary,
    ExecutionInstructionLibraryService,
)
from src.app.services.models import ModelExecutionService

from .types import PipelineRunUnavailableError


class PipelineRunSnapshotBuilder:
    """Freeze execution routing and Codex instructions when a run is created."""

    def __init__(
        self,
        *,
        model_execution_service: ModelExecutionService | None = None,
        instruction_library_service: ExecutionInstructionLibraryService | None = None,
    ) -> None:
        """Store services required by Harness-specific snapshots."""

        self._model_execution_service = model_execution_service
        self._instruction_library_service = instruction_library_service

    async def activity_snapshots(
        self,
        activities: Sequence[ActivityDocument],
        *,
        project_id: str,
        user_id: str,
        inherited_model_id: str | None,
        inherited_harness: PipelineHarness,
    ) -> tuple[dict[str, object], ...]:
        """Freeze all Activity snapshots against one instruction-library view."""

        instruction_library = await self._codex_instruction_library(
            activities=activities,
            project_id=project_id,
            user_id=user_id,
            inherited_harness=inherited_harness,
        )
        snapshots: list[dict[str, object]] = []
        for activity in activities:
            snapshots.append(
                await self._activity_snapshot(
                    activity,
                    project_id=project_id,
                    user_id=user_id,
                    inherited_model_id=inherited_model_id,
                    inherited_harness=inherited_harness,
                    instruction_library=instruction_library,
                )
            )
        return tuple(snapshots)

    async def _codex_instruction_library(
        self,
        *,
        activities: Sequence[ActivityDocument],
        project_id: str,
        user_id: str,
        inherited_harness: PipelineHarness,
    ) -> ExecutionInstructionLibrary | None:
        """Load one shared library only when a runtime Activity uses Codex."""

        requires_codex = any(
            activity.type not in ('approval', 'quiz')
            and (activity.harness or inherited_harness).kind == 'codex_cli'
            for activity in activities
        )
        if not requires_codex:
            return None
        if self._instruction_library_service is None:
            raise RuntimeError('Codex instruction snapshots are not configured.')
        return await self._instruction_library_service.load(
            user_id=user_id,
            requested_project_id=project_id,
        )

    async def _activity_snapshot(
        self,
        activity: ActivityDocument,
        *,
        project_id: str,
        user_id: str,
        inherited_model_id: str | None,
        inherited_harness: PipelineHarness,
        instruction_library: ExecutionInstructionLibrary | None,
    ) -> dict[str, object]:
        """Freeze one executable Activity in the ActivityRun wire format."""

        model_id = activity.model_id or inherited_model_id
        harness = activity.harness or inherited_harness
        config = deepcopy(activity.config)
        agents = config.get('agents')
        if isinstance(agents, list):
            config['agents'] = [
                await self._agent_snapshot(
                    agent=agent,
                    project_id=project_id,
                    user_id=user_id,
                    inherited_model_id=model_id,
                    harness=harness,
                )
                if isinstance(agent, dict)
                else agent
                for agent in agents
            ]
        execution_harness = {
            'kind': harness.kind,
            'version': harness.version,
            'config': dict(harness.config),
        }
        if activity.type in ('approval', 'quiz'):
            return {
                'id': activity.id,
                'title': activity.name,
                'description': activity.description,
                'type': activity.type,
                'executor': 'human',
                'harness': execution_harness,
                **config,
            }
        if harness.kind == 'codex_cli':
            config['requested_model'] = self._codex_requested_model(
                config=config,
                inherited_model_id=model_id,
            )
            config['instruction_snapshot'] = self._instruction_snapshot(
                config=config,
                instruction_library=instruction_library,
            )
        flows = {
            'direct_loop': 'direct',
            'refinement_loop': 'refinement',
            'roundtable_loop': 'roundtable',
        }
        flow = flows.get(activity.type)
        if flow is None:
            raise PipelineRunUnavailableError(
                pipeline_id='unknown',
                reason=f'activity {activity.id} is not executable',
            )
        return {
            'id': activity.id,
            'title': activity.name,
            'description': activity.description,
            'harness': execution_harness,
            **config,
            'flow': flow,
        }

    async def _agent_snapshot(
        self,
        *,
        agent: dict[str, object],
        project_id: str,
        user_id: str,
        inherited_model_id: str | None,
        harness: PipelineHarness,
    ) -> dict[str, object]:
        """Freeze Louie provider routing for an effective logical model ID."""

        snapshot = dict(agent)
        if harness.kind != 'louie':
            return snapshot
        model_id = snapshot.get('model_id')
        if not isinstance(model_id, str):
            model_id = inherited_model_id
        if not isinstance(model_id, str):
            raise PipelineRunUnavailableError(
                pipeline_id='unknown',
                reason='louie execution requires a model_id',
            )
        if self._model_execution_service is None:
            raise RuntimeError('Louie model execution is not configured.')
        linked_service = await self._model_execution_service.select_linked_service(
            project_id=project_id,
            model_id=model_id,
            user_id=user_id,
        )
        snapshot['model_target'] = {
            'linked_service_id': linked_service.id,
            'linked_service_user_id': linked_service.user_id,
            'model_id': model_id,
        }
        return snapshot

    @staticmethod
    def _codex_requested_model(
        *,
        config: Mapping[str, object],
        inherited_model_id: str | None,
    ) -> str:
        """Resolve the generator, Activity, Pipeline, then User Codex model."""

        agents = config.get('agents')
        generator = (
            next(
                (
                    agent
                    for agent in agents
                    if isinstance(agent, Mapping)
                    and agent.get('role') == 'generator'
                ),
                None,
            )
            if isinstance(agents, list)
            else None
        )
        model_id = generator.get('model_id') if generator is not None else None
        if not isinstance(model_id, str):
            model_id = inherited_model_id
        if not isinstance(model_id, str):
            raise PipelineRunUnavailableError(
                pipeline_id='unknown',
                reason='codex_cli execution requires a model_id',
            )
        return model_id

    @staticmethod
    def _instruction_snapshot(
        *,
        config: Mapping[str, object],
        instruction_library: ExecutionInstructionLibrary | None,
    ) -> dict[str, object]:
        """Freeze the selected Codex Persona and its ordered Skills."""

        if instruction_library is None:
            raise RuntimeError('Codex instruction snapshots are not configured.')
        agents = config.get('agents')
        if not isinstance(agents, list):
            raise PipelineRunUnavailableError(
                pipeline_id='unknown',
                reason='codex_cli execution requires one generator Persona',
            )
        generator = next(
            (
                agent
                for agent in agents
                if isinstance(agent, Mapping) and agent.get('role') == 'generator'
            ),
            None,
        )
        if generator is None or not isinstance(generator.get('persona_id'), str):
            raise PipelineRunUnavailableError(
                pipeline_id='unknown',
                reason='codex_cli execution requires one generator Persona',
            )
        return instruction_library.agent_snapshot(str(generator['persona_id']))

    @staticmethod
    def pipeline_snapshot(
        details: PipelineDetails,
        *,
        harness: PipelineHarness,
    ) -> dict[str, object]:
        """Capture graph dependencies by immutable Activity IDs."""

        return {
            'pipeline_id': details.document.id,
            'harness': {
                'kind': harness.kind,
                'version': harness.version,
                'config': dict(harness.config),
            },
            'steps': [
                {
                    'activity_id': step.activity_id,
                    'depends_on': [
                        {
                            'activity_id': dependency.activity_id,
                            'condition': dependency.condition,
                        }
                        for dependency in step.depends_on
                    ],
                }
                for step in details.document.steps
            ],
        }


def harness_snapshot(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Return a persisted Harness or the Louie compatibility value."""

    harness = snapshot.get('harness')
    if isinstance(harness, Mapping):
        return dict(harness)
    return {'kind': 'louie', 'version': 'v1', 'config': {}}
