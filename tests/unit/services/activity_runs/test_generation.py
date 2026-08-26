"""Tests for model-backed Activity-run generation."""

from __future__ import annotations

import pytest

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.catalogs.providers import ProviderId
from src.app.services.execution_instructions import (
    ExecutionInstruction,
    ExecutionInstructionLibrary,
)
from src.app.services.activity_runs.generation import (
    ActivityRunGenerationService,
    _json_object_payload,
)
from src.app.services.activity_runs.types import ActivityRunValidationError
from src.app.services.models import ModelExecutionResult


class InvalidThenValidModelExecutionService:
    """Return malformed JSON once, then a valid operation plan."""

    def __init__(self) -> None:
        """Track prompts supplied to the deterministic fake executor."""

        self.prompts: list[str] = []

    async def execute(
        self,
        *,
        prompt: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return the configured malformed response before a valid retry."""

        self.prompts.append(prompt)
        text = (
            '{"operations":[{"operation":"create","path":"output.txt",'
            '"content":"created"}],"commit_message":"feat: create output"}'
            if len(self.prompts) == 2
            else '{"operations":'
        )
        return ModelExecutionResult(
            text=text,
            provider_id=ProviderId.TOGETHER,
            model_id='model-1',
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


class NoCommitModelExecutionService:
    """Return a valid file-operation plan without a commit message."""

    def __init__(self) -> None:
        """Track whether a no-commit plan is retried unnecessarily."""

        self.prompts: list[str] = []

    async def execute(
        self,
        *,
        prompt: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return one valid operation plan without commit metadata."""

        self.prompts.append(prompt)
        return ModelExecutionResult(
            text=(
                '{"operations":[{"operation":"create","path":"output.txt",'
                '"content":"created"}]}'
            ),
            provider_id=ProviderId.TOGETHER,
            model_id='model-1',
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


class RoundtableModelExecutionService:
    """Return proposals and an operation plan for known roundtable roles."""

    def __init__(self) -> None:
        """Track model IDs invoked during roundtable generation."""

        self.model_ids: list[str] = []

    async def execute(
        self,
        *,
        model_id: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return a proposal for generators and a final plan for the aggregator."""

        self.model_ids.append(model_id)
        text = (
            '{"operations":[{"operation":"create","path":"output.txt",'
            '"content":"created"}],"commit_message":"feat: create output"}'
            if model_id == 'aggregator-model'
            else '{"proposal":"create output.txt"}'
        )
        return ModelExecutionResult(
            text=text,
            provider_id=ProviderId.TOGETHER,
            model_id=model_id,
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


class LinkedServiceModelExecutionService:
    """Record requests routed through a Persona linked-service selection."""

    def __init__(self) -> None:
        """Initialize recorded routing requests."""

        self.requests: list[tuple[str, str, str]] = []

    async def execute(
        self,
        *,
        user_id: str,
        linked_service_id: str,
        model_id: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return a valid plan using the recorded selected route."""

        self.requests.append((user_id, linked_service_id, model_id))
        return ModelExecutionResult(
            text=(
                '{"operations":[{"operation":"create","path":"output.txt",'
                '"content":"created"}],"commit_message":"feat: create output"}'
            ),
            provider_id=ProviderId.TOGETHER,
            model_id=model_id,
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


@pytest.mark.asyncio
async def test_generation_prefers_a_frozen_agent_model_target() -> None:
    """An explicit snapshot target does not require Persona routing."""

    model_execution_service = LinkedServiceModelExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=None,
    )

    await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'model_target': {
                        'linked_service_id': 'service-frozen',
                        'linked_service_user_id': 'user-frozen',
                        'model_id': 'model-frozen',
                    },
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        user_id='user-continuing-run',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={'repo_context': 'Repository context.'},
    )

    assert model_execution_service.requests == [
        ('user-frozen', 'service-frozen', 'model-frozen'),
    ]


class StaticInstructionLibraryService:
    """Return one prebuilt execution instruction library."""

    def __init__(self, library: ExecutionInstructionLibrary) -> None:
        """Store the library returned for generation."""

        self._library = library

    async def load(self, **_: object) -> ExecutionInstructionLibrary:
        """Return the fixed execution library."""

        return self._library


def selected_persona_library(
    personas_by_model_id: dict[str, str],
) -> StaticInstructionLibraryService:
    """Build a library containing instruction-only Personas."""

    personas = {
        persona_id: ExecutionInstruction(
            id=persona_id,
            source_id=persona_id,
            instruction_type='persona',
            origin=InstructionOrigin.CUSTOM,
            version=1,
            catalog_version=None,
            name=persona_id,
            description='Selected Persona.',
            content='Persona instructions.',
            metadata={},
        )
        for persona_id in personas_by_model_id
    }
    return StaticInstructionLibraryService(
        ExecutionInstructionLibrary(
            workspace_id='workspace-1',
            skills={},
            personas=personas,
            skill_aliases={},
            persona_aliases={persona_id: persona_id for persona_id in personas},
        )
    )


class RefinementModelExecutionService:
    """Return a generator plan and a rejected reviewer decision."""

    def __init__(self) -> None:
        """Track invoked model IDs and generator prompts."""

        self.model_ids: list[str] = []
        self.generator_prompts: list[str] = []

    async def execute(
        self,
        *,
        model_id: str,
        prompt: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return a role-appropriate JSON response for refinement execution."""

        self.model_ids.append(model_id)
        if model_id == 'generator-model':
            self.generator_prompts.append(prompt)
            text = (
                '{"operations":[{"operation":"create","path":"output.txt",'
                '"content":"created"}],"commit_message":"feat: create output"}'
            )
        else:
            text = '{"approved":false,"feedback":"Add a regression test."}'
        return ModelExecutionResult(
            text=text,
            provider_id=ProviderId.TOGETHER,
            model_id=model_id,
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


@pytest.mark.asyncio
async def test_refinement_generation_uses_reviewer_feedback_on_retry() -> None:
    """Refinement generators receive the rejected review from the prior iteration."""

    model_execution_service = RefinementModelExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library(
            {'persona-1': 'generator-model', 'persona-2': 'reviewer-model'}
        ),
    )
    snapshot = {
        'flow': 'refinement',
        'agents': [
            {'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'generator-model'}, 'persona_id': 'persona-1', 'role': 'generator'},
            {'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'reviewer-model'}, 'persona_id': 'persona-2', 'role': 'reviewer'},
        ],
        'output_contract': {},
    }

    context = await service.generate_context(
        loop_snapshot=snapshot,
        user_id='user-1',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={
            'repo_context': 'Repository context.',
            'review_result': {
                'approved': False,
                'reviewers': [{'feedback': 'Add a regression test.'}],
            },
        },
    )
    review = await service.generate_review_context(
        loop_snapshot=snapshot,
        input_text='Create an output file.',
        context=context,
        final_diff='diff --git a/output.txt b/output.txt',
        changed_file_contents={'output.txt': 'created'},
    )

    assert context['runtime_artifacts']['operations'][0]['path'] == 'output.txt'
    assert 'Previous reviewer feedback to address' in model_execution_service.generator_prompts[0]
    assert review == {
        'approved': False,
        'reviewers': [
            {
                'persona_id': 'persona-2',
                'approved': False,
                'feedback': 'Add a regression test.',
            },
        ],
    }


@pytest.mark.asyncio
async def test_roundtable_generation_does_not_execute_reviewers() -> None:
    """Roundtable aggregation invokes generators and its aggregator only."""

    model_execution_service = RoundtableModelExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library(
            {
                'persona-1': 'generator-1',
                'persona-2': 'generator-2',
                'persona-3': 'reviewer-model',
                'persona-4': 'aggregator-model',
            }
        ),
    )
    snapshot = {
        'flow': 'roundtable',
        'agents': [
            {'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'generator-1'}, 'persona_id': 'persona-1', 'role': 'generator'},
            {'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'generator-2'}, 'persona_id': 'persona-2', 'role': 'generator'},
            {'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'reviewer-model'}, 'persona_id': 'persona-3', 'role': 'reviewer'},
            {'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'aggregator-model'}, 'persona_id': 'persona-4', 'role': 'aggregator'},
        ],
        'output_contract': {},
    }

    context = await service.generate_context(
        loop_snapshot=snapshot,
        user_id='user-1',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={'repo_context': 'Repository context.'},
    )

    assert context['runtime_artifacts']['operations'][0]['path'] == 'output.txt'
    assert model_execution_service.model_ids == [
        'generator-1',
        'generator-2',
        'aggregator-model',
    ]
    with pytest.raises(ActivityRunValidationError):
        service.require_executable_flow(snapshot)


@pytest.mark.asyncio
async def test_generation_retries_one_invalid_json_response() -> None:
    """A malformed first model response is retried with a stricter instruction."""

    model_execution_service = InvalidThenValidModelExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library({'persona-1': 'model-1'}),
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'model-1'},
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        user_id='user-1',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={'repo_context': 'Repository context.'},
    )

    assert context['runtime_artifacts']['operations'] == [
        {
            'operation': 'create',
            'path': 'output.txt',
            'content': 'created',
        },
    ]
    assert len(model_execution_service.prompts) == 2
    assert 'Return a complete JSON object only' in model_execution_service.prompts[1]


@pytest.mark.asyncio
async def test_generation_rejects_agent_without_model_target() -> None:
    """Generation cannot derive an agent target from Persona instructions."""

    model_execution_service = LinkedServiceModelExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library({'persona-1': 'legacy-model'}),
    )

    with pytest.raises(ActivityRunValidationError, match='requires a model_target'):
        await service.generate_context(
            loop_snapshot={
                'flow': 'direct',
                'agents': [
                    {
                        'persona_id': 'persona-1',
                        'role': 'generator',
                    },
                ],
                'output_contract': {},
            },
            user_id='user-1',
            requested_workspace_id=None,
            input_text='Create an output file.',
            context={'repo_context': 'Repository context.'},
        )

    assert model_execution_service.requests == []


class FencedJsonModelExecutionService:
    """Return an otherwise valid operation plan in a Markdown JSON fence."""

    def __init__(self) -> None:
        """Track the single prompt supplied to the executor."""

        self.prompts: list[str] = []

    async def execute(
        self,
        *,
        prompt: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return one fenced operation plan."""

        self.prompts.append(prompt)
        return ModelExecutionResult(
            text=(
                '```json\n'
                '{"operations":[{"operation":"create","path":"output.txt",'
                '"content":"created"}],"commit_message":"feat: create output"}'
                '\n```'
            ),
            provider_id=ProviderId.TOGETHER,
            model_id='model-1',
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


@pytest.mark.asyncio
async def test_generation_accepts_a_markdown_fenced_json_response() -> None:
    """A valid operation plan in one JSON fence does not require a retry."""

    model_execution_service = FencedJsonModelExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library({'persona-1': 'model-1'}),
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'model-1'},
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        user_id='user-1',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={'repo_context': 'Repository context.'},
    )

    assert context['runtime_artifacts']['operations'][0]['path'] == 'output.txt'
    assert len(model_execution_service.prompts) == 1


def test_json_object_payload_accepts_prose_wrapped_json() -> None:
    """A model explanation around one object preserves the operation plan."""

    payload = _json_object_payload(
        'Here is the requested operation plan:\n'
        '{"operations":[],"commit_message":"docs: update"}\n'
        'This plan is ready to apply.'
    )

    assert payload == {'operations': [], 'commit_message': 'docs: update'}


@pytest.mark.asyncio
async def test_forbidden_commit_generation_accepts_a_plan_without_commit_message() -> None:
    """A forbid run neither requests nor retries for commit metadata."""

    model_execution_service = NoCommitModelExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library({'persona-1': 'model-1'}),
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'commit_mode': 'forbid',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'model-1'},
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        user_id='user-1',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={'repo_context': 'Repository context.'},
    )

    assert context['runtime_artifacts'] == {
        'operations': [
            {'operation': 'create', 'path': 'output.txt', 'content': 'created'},
        ],
    }
    assert len(model_execution_service.prompts) == 1
    assert 'commit_message' not in model_execution_service.prompts[0]


class EmptyThenValidPlanExecutionService:
    """Return an empty operation plan once, then the required file change."""

    def __init__(self) -> None:
        """Track prompts supplied to the deterministic fake executor."""

        self.prompts: list[str] = []

    async def execute(
        self,
        *,
        prompt: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return a valid non-empty plan after the correction request."""

        self.prompts.append(prompt)
        text = (
            '{"operations":[{"operation":"create","path":"output.txt",'
            '"content":"created"}],"commit_message":"feat: create output"}'
            if len(self.prompts) == 2
            else '{"operations": []}'
        )
        return ModelExecutionResult(
            text=text,
            provider_id=ProviderId.TOGETHER,
            model_id='model-1',
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


class ApiExampleThenValidPlanExecutionService:
    """Return an API example before a valid file-operation plan."""

    def __init__(self) -> None:
        """Track prompts supplied to the deterministic fake executor."""

        self.prompts: list[str] = []

    async def execute(
        self,
        *,
        prompt: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return a valid file-operation plan after the correction request."""

        self.prompts.append(prompt)
        text = (
            '{"operations":[{"operation":"create","path":"output.txt",'
            '"content":"created"}],"commit_message":"feat: create output"}'
            if len(self.prompts) == 2
            else '{"errorCode":"invalid-response","message":"Malformed response"}'
        )
        return ModelExecutionResult(
            text=text,
            provider_id=ProviderId.TOGETHER,
            model_id='model-1',
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


@pytest.mark.asyncio
async def test_generation_retries_an_api_example_response() -> None:
    """An API-shaped response is corrected into a file-operation plan."""

    model_execution_service = ApiExampleThenValidPlanExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library({'persona-1': 'model-1'}),
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'model-1'},
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        user_id='user-1',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={'repo_context': 'Repository context.'},
    )

    assert context['runtime_artifacts']['operations'][0]['path'] == 'output.txt'
    assert len(model_execution_service.prompts) == 2
    assert 'only top-level keys are operations and commit_message' in (
        model_execution_service.prompts[1]
    )


@pytest.mark.asyncio
async def test_generation_retries_one_empty_operation_plan() -> None:
    """An empty operation plan is retried with an explicit change requirement."""

    model_execution_service = EmptyThenValidPlanExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library({'persona-1': 'model-1'}),
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'model-1'},
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        user_id='user-1',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={'repo_context': 'Repository context.'},
    )

    assert context['runtime_artifacts']['operations'][0]['path'] == 'output.txt'
    assert len(model_execution_service.prompts) == 2
    assert 'operations must be a non-empty array' in model_execution_service.prompts[1]


class MissingCommitThenValidPlanExecutionService:
    """Return a plan without a commit message before a valid correction."""

    def __init__(self) -> None:
        """Track prompts supplied to the deterministic fake executor."""

        self.prompts: list[str] = []

    async def execute(
        self,
        *,
        prompt: str,
        **_: object,
    ) -> ModelExecutionResult:
        """Return a commit message only after the correction request."""

        self.prompts.append(prompt)
        text = (
            '{"operations":[{"operation":"create","path":"output.txt",'
            '"content":"created"}],"commit_message":"feat: create output"}'
            if len(self.prompts) == 2
            else '{"operations":[{"operation":"create","path":"output.txt",'
            '"content":"created"}]}'
        )
        return ModelExecutionResult(
            text=text,
            provider_id=ProviderId.TOGETHER,
            model_id='model-1',
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


@pytest.mark.asyncio
async def test_generation_retries_one_plan_without_commit_message() -> None:
    """A final plan without a commit message gets one correction request."""

    model_execution_service = MissingCommitThenValidPlanExecutionService()
    service = ActivityRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=selected_persona_library({'persona-1': 'model-1'}),
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'model_target': {'linked_service_id': 'service-1', 'linked_service_user_id': 'user-1', 'model_id': 'model-1'},
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        user_id='user-1',
        requested_workspace_id=None,
        input_text='Create an output file.',
        context={'repo_context': 'Repository context.'},
    )

    assert context['runtime_artifacts']['commit_message'] == 'feat: create output'
    assert len(model_execution_service.prompts) == 2
    assert 'commit_message must be a non-empty string' in (
        model_execution_service.prompts[1]
    )
