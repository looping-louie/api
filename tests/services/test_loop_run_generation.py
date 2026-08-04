"""Tests for model-backed loop-run generation."""

from __future__ import annotations

import pytest

from src.app.catalogs.providers import ProviderId
from src.app.services.loop_runs.generation import LoopRunGenerationService
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
            '"content":"created"}]}'
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
            '"content":"created"}]}'
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
    assert 'Return a non-empty operations array' in model_execution_service.prompts[1]