"""Model orchestration for direct, refinement, and roundtable loop runs."""

from __future__ import annotations

import json
import logging
from typing import Mapping

from src.app.services.execution_instructions import (
    ExecutionInstructionLibrary,
    ExecutionInstructionLibraryService,
)
from src.app.services.activity_runs.types import ActivityRunValidationError
from src.app.services.model_execution import (
    ModelExecutionError,
    ModelExecutionService,
    ModelOutputValidationError,
)
from src.app.services.task_checkpoint import parse_file_operations


LOGGER = logging.getLogger(__name__)
MAX_JSON_RESPONSE_ATTEMPTS = 2


def _json_object_payload(text: str) -> object:
    """Decode JSON output, accepting a fenced or prose-wrapped model object."""

    candidate = text.strip()
    lines = candidate.splitlines()
    if (
        len(lines) >= 2
        and lines[0].strip().casefold() in {'```', '```json'}
        and lines[-1].strip() == '```'
    ):
        candidate = '\n'.join(lines[1:-1]).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as error:
        decoder = json.JSONDecoder()
        for index, character in enumerate(candidate):
            if character != '{':
                continue
            try:
                payload, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            return payload
        raise error


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
        """Generate a final operation plan for a loop activity."""

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
        require_commit_message = loop_snapshot.get('commit_mode') != 'forbid'
        return await self._generate_operation_context(
            workspace_id=workspace_id,
            agent=generators[0],
            prompt=self._agent_prompt(
                agent=generators[0],
                prompt=self._operation_prompt(
                    input_text=input_text,
                    repo_context=str(context['repo_context']),
                    output_contract=self._output_contract(loop_snapshot),
                    reviewer_feedback=self._reviewer_feedback(context),
                    require_commit_message=require_commit_message,
                ),
                instruction_library=instruction_library,
            ),
            context=context,
            instruction_library=instruction_library,
            require_commit_message=require_commit_message,
        )
    async def _generate_roundtable_context(
        self,
        *,
        loop_snapshot: Mapping[str, object],
        workspace_id: str,
        input_text: str,
        context: dict[str, object],
        instruction_library: ExecutionInstructionLibrary | None,
    ) -> dict[str, object]:
        """Aggregate generator proposals into one final operation plan."""

        generators = self._agents_for_role(loop_snapshot, 'generator')
        aggregators = self._agents_for_role(loop_snapshot, 'aggregator')
        output_contract = self._output_contract(loop_snapshot)
        require_commit_message = loop_snapshot.get('commit_mode') != 'forbid'
        proposal_prompt = (
            'Return only a JSON object proposing a solution for this task.\n\n'
            'Keep the proposal under 600 words; do not draft the output file.\n\n'
            f'Task:\n{input_text}\n\n'
            f'Output contract:\n{json.dumps(output_contract)}\n\n'
            f'Repository context:\n{context["repo_context"]}'
            f'{self._reviewer_feedback(context)}'
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
                instruction_library,
            )
            for agent in generators
        ]
        aggregation_prompt = (
            f'{self._operation_prompt(\
                input_text=input_text,\
                repo_context=str(context["repo_context"]),\
                output_contract=output_contract,\
                reviewer_feedback=self._reviewer_feedback(context),\
                require_commit_message=require_commit_message,
            )}'
            f'\n\nGenerator proposals:\n{json.dumps(proposals)}'
        )
        return await self._generate_operation_context(
            workspace_id=workspace_id,
            agent=aggregators[0],
            prompt=self._agent_prompt(
                agent=aggregators[0],
                prompt=aggregation_prompt,
                instruction_library=instruction_library,
            ),
            context=context,
            instruction_library=instruction_library,
            require_commit_message=require_commit_message,
        )

    async def _generate_operation_context(
        self,
        *,
        workspace_id: str,
        agent: Mapping[str, object],
        prompt: str,
        context: dict[str, object],
        instruction_library: ExecutionInstructionLibrary | None = None,
        require_commit_message: bool = True,
    ) -> dict[str, object]:
        """Generate one non-empty CLI operation plan with one corrective retry."""

        retry_prompt = prompt
        for attempt in range(MAX_JSON_RESPONSE_ATTEMPTS):
            generated = await self._execute_agent(
                workspace_id,
                agent,
                retry_prompt,
                instruction_library,
            )
            try:
                return self._with_runtime_artifacts(
                    context,
                    generated,
                    require_commit_message=require_commit_message,
                )
            except ModelExecutionError:
                if attempt + 1 == MAX_JSON_RESPONSE_ATTEMPTS:
                    raise
                retry_prompt = (
                    f'{prompt}\n\nYour previous response was not a valid file '
                    'operation plan. Return exactly one JSON object whose only '
                    'top-level keys are operations'
                    f'{" and commit_message" if require_commit_message else ""}. Do not '
                    'return an API response example, schema, error object, or '
                    'check result. operations must be a non-empty array of file '
                    'changes required to complete the task'
                    f'{", and commit_message must be a non-empty string" if require_commit_message else ""}.'
                )

        raise AssertionError('Operation plan retry attempts were exhausted.')

    async def generate_review_context(
        self,
        *,
        loop_snapshot: Mapping[str, object],
        workspace_id: str,
        input_text: str,
        context: Mapping[str, object],
        final_diff: str,
        changed_file_contents: Mapping[str, str],
    ) -> dict[str, object]:
        """Return configured reviewer approval for locally applied changes."""

        reviewers = [
            agent
            for agent in self._agents(loop_snapshot)
            if agent.get('role') == 'reviewer'
        ]
        if not reviewers:
            return {'approved': True, 'reviewers': []}

        review_prompt = (
            'Return only a JSON object with an approved boolean and feedback '
            'string. Approve only when the applied change satisfies the task '
            'and output contract.\n\n'
            f'Task:\n{input_text}\n\n'
            f'Output contract:\n{json.dumps(self._output_contract(loop_snapshot))}\n\n'
            f'Repository context:\n{context["repo_context"]}\n\n'
            f'Applied diff:\n{final_diff}\n\n'
            f'Changed file contents:\n{json.dumps(changed_file_contents)}'
        )
        reviews: list[dict[str, object]] = []
        for reviewer in reviewers:
            review = await self._execute_agent(
                workspace_id,
                reviewer,
                review_prompt,
            )
            approved = review.get('approved')
            feedback = review.get('feedback')
            if not isinstance(approved, bool) or not isinstance(feedback, str):
                raise ModelExecutionError(
                    'Loop reviewer returned an invalid review decision.'
                )
            reviews.append(
                {
                    'persona_id': reviewer['persona_id'],
                    'approved': approved,
                    'feedback': feedback,
                }
            )

        return {
            'approved': all(review['approved'] for review in reviews),
            'reviewers': reviews,
        }
    @staticmethod
    def require_executable_flow(snapshot: Mapping[str, object]) -> None:
        """Require a direct or selected roundtable role configuration."""

        flow = snapshot.get('flow')
        if flow not in {'direct', 'roundtable'}:
            raise ActivityRunValidationError(
                field_name='flow',
                message='is not yet supported for execution',
            )
        agents = LoopRunGenerationService._agents(snapshot)
        if flow == 'direct' and any(
            agent.get('role') in {'reviewer', 'aggregator'} for agent in agents
        ):
            raise ActivityRunValidationError(
                field_name='agents',
                message='direct execution requires generators only',
            )
        if flow == 'direct' and len(
            LoopRunGenerationService._agents_for_role(snapshot, 'generator')
        ) != 1:
            raise ActivityRunValidationError(
                field_name='agents',
                message='direct execution requires one generator',
            )
        if flow == 'roundtable':
            if any(agent.get('role') == 'reviewer' for agent in agents):
                raise ActivityRunValidationError(
                    field_name='agents',
                    message='roundtable execution does not allow reviewers',
                )
            if len(
                LoopRunGenerationService._agents_for_role(
                    snapshot,
                    'generator',
                )
            ) < 2:
                raise ActivityRunValidationError(
                    field_name='agents',
                    message='roundtable execution requires two generators',
                )
            if len(
                LoopRunGenerationService._agents_for_role(
                    snapshot,
                    'aggregator',
                )
            ) != 1:
                raise ActivityRunValidationError(
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
        instruction_library: ExecutionInstructionLibrary | None = None,
    ) -> dict[str, object]:
        """Execute one configured agent and require a JSON object response."""

        role = str(agent['role'])
        model_id = str(agent['model_id'])
        linked_service_selection = (
            instruction_library.persona_linked_service_selection(
                str(agent['persona_id']),
            )
            if instruction_library is not None
            else None
        )
        if linked_service_selection is None:
            raise ActivityRunValidationError(
                field_name='agents',
                message='Persona requires a linked-service selection.',
            )
        retry_prompt = prompt
        for attempt in range(MAX_JSON_RESPONSE_ATTEMPTS):
            try:
                result = await self._model_execution_service.execute(
                    workspace_id=workspace_id,
                    linked_service_id=linked_service_selection.linked_service_id,
                    model_id=linked_service_selection.model_id,
                    prompt=retry_prompt,
                    json_mode=True,
                )
            except ModelExecutionError as error:
                LOGGER.warning(
                    'Loop agent execution failed: role=%s model_id=%s error=%s',
                    role,
                    model_id,
                    error,
                )
                raise ModelExecutionError(
                    f'Loop {role} agent execution failed.'
                ) from error
            try:
                payload = _json_object_payload(result.text)
            except json.JSONDecodeError as error:
                if attempt + 1 == MAX_JSON_RESPONSE_ATTEMPTS:
                    LOGGER.warning(
                        'Loop agent returned invalid JSON: role=%s model_id=%s',
                        role,
                        model_id,
                    )
                    raise ModelOutputValidationError(
                        f'Loop {role} agent returned invalid JSON.'
                    ) from error
                retry_prompt = (
                    f'{prompt}\n\nReturn a complete JSON object only; do not '
                    'include Markdown or explanatory text.'
                )
                continue
            if isinstance(payload, dict):
                return payload
            LOGGER.warning(
                'Loop agent returned a non-object JSON response: '
                'role=%s model_id=%s',
                role,
                model_id,
            )
            raise ModelOutputValidationError(
                f'Loop {role} agent response must be a JSON object.'
            )

        raise AssertionError('JSON response retry attempts were exhausted.')

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
            raise ActivityRunValidationError(
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
        reviewer_feedback: str = '',
        require_commit_message: bool = True,
    ) -> str:
        """Build the prompt that requires a CLI-compatible operation plan."""

        return (
            'Return only a JSON object with a non-empty operations array'
            f'{" and commit_message" if require_commit_message else ""}. '
            'Operations must use create, replace, replace_text, '
            'or delete. Use this shape: '
            '{"operations":[{"operation":"create","path":"ideas.md",'
            '"content":"..."}]'
            f'{",\"commit_message\":\"docs: add ideas\"" if require_commit_message else ""}'
            '}. '
            f'\n\nTask:\n{input_text}\n\nOutput contract:\n'
            f'{json.dumps(output_contract)}\n\nRepository context:\n{repo_context}'
            f'{reviewer_feedback}'
        )

    @staticmethod
    def _reviewer_feedback(context: Mapping[str, object]) -> str:
        """Format prior reviewer rejection feedback for a new iteration."""

        review_result = context.get('review_result')
        if not isinstance(review_result, Mapping) or review_result.get('approved') is True:
            return ''
        reviewers = review_result.get('reviewers')
        if not isinstance(reviewers, list):
            return ''
        feedback = [
            review.get('feedback')
            for review in reviewers
            if isinstance(review, Mapping) and isinstance(review.get('feedback'), str)
        ]
        return (
            f'\n\nPrevious reviewer feedback to address:\n{json.dumps(feedback)}'
            if feedback
            else ''
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
        *,
        require_commit_message: bool,
    ) -> dict[str, object]:
        """Validate and expose the final operation plan to the CLI."""

        try:
            operations = parse_file_operations(
                json.dumps(generated),
                require_non_empty=True,
            )
        except ValueError as error:
            LOGGER.warning(
                'Loop agent returned an invalid operation plan: keys=%s error=%s',
                sorted(generated),
                error,
            )
            raise ModelOutputValidationError(
                'Loop agent returned an invalid operation plan.'
            ) from error
        commit_message = generated.get('commit_message')
        if require_commit_message and (
            not isinstance(commit_message, str) or not commit_message.strip()
        ):
            LOGGER.warning(
                'Loop agent returned an operation plan without a commit message: '
                'keys=%s commit_message_type=%s',
                sorted(generated),
                type(commit_message).__name__,
            )
            raise ModelOutputValidationError(
                'Loop agent returned an operation plan without a commit message.'
            )
        runtime_artifacts: dict[str, object] = {
            'operations': operations,
        }
        if isinstance(commit_message, str) and commit_message.strip():
            runtime_artifacts['commit_message'] = commit_message
        return {
            **context,
            'runtime_artifacts': runtime_artifacts,
        }
