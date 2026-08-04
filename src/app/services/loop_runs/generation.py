"""Model orchestration for direct and roundtable loop runs."""

from __future__ import annotations

import json
from typing import Mapping

from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibrary,
    ExecutionInstructionLibraryService,
)
from src.app.services.loops.types import LoopValidationError
from src.app.services.model_execution import (
    ModelExecutionError,
    ModelExecutionService,
)
from src.app.services.task_checkpoint import parse_file_operations

class LoopRunGenerationService:
    """Generate one final CLI operation plan from a loop snapshot."""

    def __init__(
        self,
        *,
        model_execution_service: ModelExecutionService,
        instruction_library_service: ExecutionInstructionLibraryService | None,
    ) -> None:
        """Store services used to invoke models and resolve personas."""

        self._model_execution_service = model_execution_service
        self._instruction_library_service = instruction_library_service
    async def generate_context(
        self,
        *,
        loop_snapshot: Mapping[str, object],
        workspace_id: str,
        user_id: str,
        requested_workspace_id: str | None,
        input_text: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        """Generate a final operation plan for a direct or roundtable loop."""

        instruction_library = await self._load_instruction_library(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        if loop_snapshot.get('flow') == 'roundtable':
            return await self._generate_roundtable_context(
                loop_snapshot=loop_snapshot,
                workspace_id=workspace_id,
                input_text=input_text,
                context=context,
                instruction_library=instruction_library,
            )
        generators = self._agents_for_role(loop_snapshot, 'generator')
        generated = await self._execute_agent(
            workspace_id,
            generators[0],
            self._agent_prompt(
                agent=generators[0],
                prompt=self._operation_prompt(
                    input_text=input_text,
                    repo_context=str(context['repo_context']),
                    output_contract=self._output_contract(loop_snapshot),
                ),
                instruction_library=instruction_library,
            ),
        )
        return self._with_runtime_artifacts(context, generated)
    async def _generate_roundtable_context(
        self,
        *,
        loop_snapshot: Mapping[str, object],
        workspace_id: str,
        input_text: str,
        context: dict[str, object],
        instruction_library: ExecutionInstructionLibrary | None,
    ) -> dict[str, object]:
        """Aggregate generator proposals and reviewer critique into one plan."""

        generators = self._agents_for_role(loop_snapshot, 'generator')
        reviewers = self._agents_for_role(loop_snapshot, 'reviewer')
        aggregators = self._agents_for_role(loop_snapshot, 'aggregator')
        output_contract = self._output_contract(loop_snapshot)
        proposal_prompt = (
            'Return only a JSON object proposing a solution for this task.\n\n'
            f'Task:\n{input_text}\n\n'
            f'Output contract:\n{json.dumps(output_contract)}\n\n'
            f'Repository context:\n{context["repo_context"]}'
        )
        proposals = [
            await self._execute_agent(
                workspace_id,
                agent,
                self._agent_prompt(
                    agent=agent,
                    prompt=proposal_prompt,
                    instruction_library=instruction_library,
                ),
            )
            for agent in generators
        ]
        review_prompt = (
            'Return only a JSON object critiquing these candidate proposals '
            f'for the task.\n\nTask:\n{input_text}\n\n'
            f'Output contract:\n{json.dumps(output_contract)}\n\n'
            f'Repository context:\n{context["repo_context"]}'
            f'\n\nProposals:\n{json.dumps(proposals)}'
        )
        critiques = [
            await self._execute_agent(
                workspace_id,
                agent,
                self._agent_prompt(
                    agent=agent,
                    prompt=review_prompt,
                    instruction_library=instruction_library,
                ),
            )
            for agent in reviewers
        ]
        aggregation_prompt = (
            f'{self._operation_prompt(\
                input_text=input_text,\
                repo_context=str(context["repo_context"]),\
                output_contract=output_contract,\
            )}'
            f'\n\nGenerator proposals:\n{json.dumps(proposals)}'
            f'\n\nReviewer critique:\n{json.dumps(critiques)}'
        )
        aggregated = await self._execute_agent(
            workspace_id,
            aggregators[0],
            self._agent_prompt(
                agent=aggregators[0],
                prompt=aggregation_prompt,
                instruction_library=instruction_library,
            ),
        )
        return self._with_runtime_artifacts(context, aggregated)
    @staticmethod
    def require_executable_flow(snapshot: Mapping[str, object]) -> None:
        """Require a direct or selected roundtable role configuration."""

        flow = snapshot.get('flow')
        if flow not in {'direct', 'roundtable'}:
            raise LoopValidationError(
                field_name='flow',
                message='is not yet supported for execution',
            )
        agents = LoopRunGenerationService._agents(snapshot)
        if flow == 'direct' and any(
            agent.get('role') in {'reviewer', 'aggregator'} for agent in agents
        ):
            raise LoopValidationError(
                field_name='agents',
                message='direct execution requires generators only',
            )
        if flow == 'roundtable':
            if len(
                LoopRunGenerationService._agents_for_role(
                    snapshot,
                    'generator',
                )
            ) < 2:
                raise LoopValidationError(
                    field_name='agents',
                    message='roundtable execution requires two generators',
                )
            if len(
                LoopRunGenerationService._agents_for_role(
                    snapshot,
                    'aggregator',
                )
            ) != 1:
                raise LoopValidationError(
                    field_name='agents',
                    message='roundtable execution requires one aggregator',
                )

    async def _load_instruction_library(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> ExecutionInstructionLibrary | None:
        """Load persona content when the application provides a library."""

        if self._instruction_library_service is None:
            return None
        return await self._instruction_library_service.load(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

    async def _execute_agent(
        self,
        workspace_id: str,
        agent: Mapping[str, object],
        prompt: str,
    ) -> dict[str, object]:
        """Execute one configured agent and require a JSON object response."""

        result = await self._model_execution_service.execute(
            workspace_id=workspace_id,
            model_id=str(agent['model_id']),
            prompt=prompt,
        )
        try:
            payload = json.loads(result.text)
        except json.JSONDecodeError as error:
            raise ModelExecutionError('Loop agent returned invalid JSON.') from error
        if not isinstance(payload, dict):
            raise ModelExecutionError('Loop agent response must be a JSON object.')
        return payload

    @staticmethod
    def _agents(snapshot: Mapping[str, object]) -> list[Mapping[str, object]]:
        """Return serialized loop agents as mapping values only."""

        agents = snapshot.get('agents')
        if not isinstance(agents, (list, tuple)):
            return []
        return [agent for agent in agents if isinstance(agent, Mapping)]

    @classmethod
    def _agents_for_role(
        cls,
        snapshot: Mapping[str, object],
        role: str,
    ) -> list[Mapping[str, object]]:
        """Return agents assigned to a role or reject an invalid execution flow."""

        agents = [
            agent for agent in cls._agents(snapshot) if agent.get('role') == role
        ]
        if not agents:
            raise LoopValidationError(
                field_name='agents',
                message=f'requires at least one {role}',
            )
        return agents

    @staticmethod
    def _operation_prompt(
        *,
        input_text: str,
        repo_context: str,
        output_contract: Mapping[str, object],
    ) -> str:
        """Build the prompt that requires a CLI-compatible operation plan."""

        return (
            'Return only a JSON object with an operations array and an optional '
            'commit_message. Operations must use create, replace, replace_text, '
            f'or delete.\n\nTask:\n{input_text}\n\nOutput contract:\n'
            f'{json.dumps(output_contract)}\n\nRepository context:\n{repo_context}'
        )

    @staticmethod
    def _agent_prompt(
        *,
        agent: Mapping[str, object],
        prompt: str,
        instruction_library: ExecutionInstructionLibrary | None,
    ) -> str:
        """Prefix a model prompt with its configured persona instruction."""

        if instruction_library is None:
            return prompt
        persona_content = instruction_library.persona_content(
            str(agent['persona_id']),
        )
        return f'Persona instructions:\n{persona_content}\n\n{prompt}'

    @staticmethod
    def _output_contract(
        snapshot: Mapping[str, object],
    ) -> Mapping[str, object]:
        """Return the persisted output contract used to guide model output."""

        contract = snapshot.get('output_contract')
        return contract if isinstance(contract, Mapping) else {}

    @staticmethod
    def _with_runtime_artifacts(
        context: dict[str, object],
        generated: dict[str, object],
    ) -> dict[str, object]:
        """Validate and expose the final operation plan to the CLI."""

        operations = parse_file_operations(json.dumps(generated))
        return {
            **context,
            'runtime_artifacts': {
                'operations': operations,
                'commit_message': generated.get('commit_message'),
            },
        }
