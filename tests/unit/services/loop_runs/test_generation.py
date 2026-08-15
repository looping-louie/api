"""Tests for model-backed loop-run generation."""

from __future__ import annotations

import pytest

from src.app.catalogs.providers import ProviderId
from src.app.services.loop_runs.generation import (
    LoopRunGenerationService,
    _json_object_payload,
)
from src.app.services.loops.types import LoopValidationError
from src.app.services.model_execution import ModelExecutionResult


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


@pytest.mark.asyncio
async def test_roundtable_generation_does_not_execute_reviewers() -> None:
    """Roundtable aggregation invokes generators and its aggregator only."""

    model_execution_service = RoundtableModelExecutionService()
    service = LoopRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=None,
    )
    snapshot = {
        'flow': 'roundtable',
        'agents': [
            {'model_id': 'generator-1', 'persona_id': 'persona-1', 'role': 'generator'},
            {'model_id': 'generator-2', 'persona_id': 'persona-2', 'role': 'generator'},
            {'model_id': 'reviewer-model', 'persona_id': 'persona-3', 'role': 'reviewer'},
            {'model_id': 'aggregator-model', 'persona_id': 'persona-4', 'role': 'aggregator'},
        ],
        'output_contract': {},
    }

    context = await service.generate_context(
        loop_snapshot=snapshot,
        workspace_id='workspace-1',
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
    with pytest.raises(LoopValidationError):
        service.require_executable_flow(snapshot)


@pytest.mark.asyncio
async def test_generation_retries_one_invalid_json_response() -> None:
    """A malformed first model response is retried with a stricter instruction."""

    model_execution_service = InvalidThenValidModelExecutionService()
    service = LoopRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=None,
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        workspace_id='workspace-1',
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
    service = LoopRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=None,
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        workspace_id='workspace-1',
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
    service = LoopRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=None,
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        workspace_id='workspace-1',
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
    service = LoopRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=None,
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        workspace_id='workspace-1',
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
    service = LoopRunGenerationService(
        model_execution_service=model_execution_service,
        instruction_library_service=None,
    )

    context = await service.generate_context(
        loop_snapshot={
            'flow': 'direct',
            'agents': [
                {
                    'id': 'agent-1',
                    'model_id': 'model-1',
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
            'output_contract': {},
        },
        workspace_id='workspace-1',
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
