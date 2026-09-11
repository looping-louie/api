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
from src.app.services.models.availability import ModelNotFoundError
from src.app.services.models.catalog import ModelCatalogService

from .types import PipelineRunUnavailableError


class PipelineRunSnapshotBuilder:
    """Freeze execution routing and CLI instructions when a run is created."""

    def __init__(
        self,
        *,
        model_execution_service: ModelExecutionService | None = None,
        model_catalog_service: ModelCatalogService | None = None,
        instruction_library_service: ExecutionInstructionLibraryService | None = None,
    ) -> None:
        """Store services required by Harness-specific snapshots."""

        self._model_execution_service = model_execution_service
        self._model_catalog_service = model_catalog_service
        self._instruction_library_service = instruction_library_service

    async def activity_snapshots(
        self,
        activities: Sequence[ActivityDocument],
        *,
        pipeline_id: str,
        project_id: str,
        user_id: str,
        inherited_model_id: str | None,
        inherited_harness: PipelineHarness,
    ) -> tuple[dict[str, object], ...]:
        """Freeze all Activity snapshots against one instruction-library view."""

        instruction_library = await self._cli_instruction_library(
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
                    pipeline_id=pipeline_id,
                    project_id=project_id,
                    user_id=user_id,
                    inherited_model_id=inherited_model_id,
                    inherited_harness=inherited_harness,
                    instruction_library=instruction_library,
                )
            )
        return tuple(snapshots)

    async def _cli_instruction_library(
        self,
        *,
        activities: Sequence[ActivityDocument],
        project_id: str,
        user_id: str,
        inherited_harness: PipelineHarness,
    ) -> ExecutionInstructionLibrary | None:
        """Load one shared library only when a runtime Activity uses a CLI Harness."""

        requires_cli = any(
            activity.type not in ('approval', 'quiz')
            and (activity.harness or inherited_harness).kind in (
                'codex_cli', 'copilot_cli'
            )
            for activity in activities
        )
        if not requires_cli:
            return None
        if self._instruction_library_service is None:
            raise RuntimeError('CLI instruction snapshots are not configured.')
        return await self._instruction_library_service.load(
            user_id=user_id,
            requested_project_id=project_id,
        )

    async def _activity_snapshot(
        self,
        activity: ActivityDocument,
        *,
        pipeline_id: str,
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
                    pipeline_id=pipeline_id,
                    activity_id=activity.id,
                    project_id=project_id,
                    user_id=user_id,
                    inherited_model_id=model_id,
                    harness=harness,
                    instruction_library=instruction_library,
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
        if harness.kind in ('codex_cli', 'copilot_cli'):
            requested_model = self._cli_requested_model(
                config=config,
                inherited_model_id=model_id,
                pipeline_id=pipeline_id,
                activity_id=activity.id,
            )
            config['requested_model'] = requested_model
            generator = next(
                agent for agent in config['agents']
                if isinstance(agent, Mapping) and agent.get('role') == 'generator'
            )
            config['instruction_snapshot'] = generator['instruction_snapshot']
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
        pipeline_id: str,
        activity_id: str,
        project_id: str,
        user_id: str,
        inherited_model_id: str | None,
        harness: PipelineHarness,
        instruction_library: ExecutionInstructionLibrary | None,
    ) -> dict[str, object]:
        """Freeze one agent's model route and Harness instructions."""

        snapshot = dict(agent)
        model_id = snapshot.get('model_id')
        if not isinstance(model_id, str):
            model_id = inherited_model_id
        if not isinstance(model_id, str):
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f'{harness.kind} execution requires a model_id',
                reason_code='missing_effective_model',
                activity_id=activity_id,
            )
        if harness.kind in ('codex_cli', 'copilot_cli'):
            await self._require_cli_model_enabled(
                user_id=user_id,
                pipeline_id=pipeline_id,
                activity_id=activity_id,
                model_id=model_id,
            )
            persona_id = snapshot.get('persona_id')
            if not isinstance(persona_id, str) or instruction_library is None:
                raise PipelineRunUnavailableError(
                    pipeline_id=pipeline_id,
                    reason='CLI Harness execution requires a Persona for every agent',
                    activity_id=activity_id,
                )
            snapshot['requested_model'] = model_id
            snapshot['instruction_snapshot'] = instruction_library.agent_snapshot(
                persona_id,
            )
            return snapshot
        if harness.kind != 'louie':
            return snapshot
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
    def _cli_requested_model(
        *,
        config: Mapping[str, object],
        inherited_model_id: str | None,
        pipeline_id: str,
        activity_id: str,
    ) -> str:
        """Resolve the generator, Activity, Pipeline, then User CLI model."""

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
                pipeline_id=pipeline_id,
                reason='CLI Harness execution requires a model_id',
                reason_code='missing_effective_model',
                activity_id=activity_id,
            )
        return model_id

    async def _require_cli_model_enabled(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        activity_id: str,
        model_id: str,
    ) -> None:
        """Reject CLI Harness selections absent from or disabled in the User catalog."""

        if self._model_catalog_service is None:
            return
        try:
            model = await self._model_catalog_service.describe(
                user_id=user_id,
                model_id=model_id,
            )
        except ModelNotFoundError as error:
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f"model '{model_id}' is not in the catalog",
                reason_code='model_not_found',
                activity_id=activity_id,
                model_id=model_id,
            ) from error
        if model.status == 'deprecated':
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f"model '{model_id}' is deprecated",
                reason_code='model_deprecated',
                activity_id=activity_id,
                model_id=model_id,
            )
        if not model.enabled:
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f"model '{model_id}' is disabled",
                reason_code='model_disabled',
                activity_id=activity_id,
                model_id=model_id,
            )

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
