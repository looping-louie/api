import asyncio
from types import MappingProxyType

import pytest

from src.app.controllers import task
from src.app.catalogs.instructions import InstructionOrigin
from src.app.schemas import (
    ExecutionPlan,
    GeneratorAssignment,
    ReviewerAssignment,
)
from src.app.schemas.task import ContinueRequest, StartRequest
from src.app.services.execution_instruction_library import (
    ExecutionInstruction,
    ExecutionInstructionLibrary,
)


VALID_PROJECT_PROFILE = {
    'source_file_count': 12,
    'approximate_source_chars': 2048,
    'extension_counts': {
        '.py': 10,
        '.md': 2,
    },
    'top_level_entries': [
        'src/',
        'tests/',
        'README.md',
    ],
    'markers': {
        'nuxt': False,
        'package_json': False,
        'fastapi': True,
        'docker': False,
        'tests': True,
    },
}


def execution_instruction_library() -> ExecutionInstructionLibrary:
    """Return the SQL-resolved instruction shape required by task tests."""

    skill = ExecutionInstruction(
        id='small_patch_quality',
        source_id='builtin:skill:small_patch_quality',
        instruction_type='skill',
        origin=InstructionOrigin.BUILTIN,
        version=1,
        catalog_version=1,
        name='Small patch quality',
        description='Review a small patch.',
        content='Review the patch carefully.',
        metadata={
            'applies_when': ['code'],
            'applies_to': ['generator', 'reviewer'],
            'reviewer_default_strictness': {
                'prototype': 50,
                'mvp': 55,
                'production': 70,
            },
        },
    )
    persona = ExecutionInstruction(
        id='tech_lead',
        source_id='builtin:persona:tech_lead',
        instruction_type='persona',
        origin=InstructionOrigin.BUILTIN,
        version=1,
        catalog_version=1,
        name='Tech Lead',
        description='Lead technical implementation.',
        content='Act as the technical lead.',
        metadata={
            'applies_when': ['engineering'],
            'applies_to': ['generator', 'reviewer'],
            'default_for': ['generator', 'reviewer'],
        },
        skill_ids=('builtin:skill:small_patch_quality',),
    )
    return ExecutionInstructionLibrary(
        workspace_id='workspace-1',
        skills=MappingProxyType({skill.id: skill}),
        personas=MappingProxyType({persona.id: persona}),
        skill_aliases=MappingProxyType(
            {
                skill.id: skill.id,
                skill.source_id: skill.id,
            }
        ),
        persona_aliases=MappingProxyType(
            {
                persona.id: persona.id,
                persona.source_id: persona.id,
            }
        ),
    )


async def start_task_with_library(request: StartRequest):
    return await task.start_task(
        request,
        instruction_library=execution_instruction_library(),
    )


def test_request_schema_rejects_invalid_project_profile():
    with pytest.raises(ValueError):
        StartRequest(
            repo_path='/tmp/repo',
            constitution='Implement only the requested task.',
            project_profile={
                'source_file_count': 12,
                # Missing required fields:
                # approximate_source_chars, extension_counts,
                # top_level_entries, markers
            },
            task={
                'id': 'task-004',
                'status': 'pending',
                'prompt': 'Implement small change',
                'run_id': None,
                'commit_message': 'feat: implement small change',
            },
        )


def test_task_checkpoint_start_returns_first_action():
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    request = StartRequest(
        repo_path='/tmp/repo',
        constitution='Implement only the requested task.',
        project_profile=VALID_PROJECT_PROFILE,
        task={
            'id': 'task-checkpoint-001',
            'status': 'pending',
            'prompt': 'Implement checkpoint flow',
            'run_id': None,
            'commit_message': 'feat: checkpoint start',
        },
    )

    result = asyncio.run(start_task_with_library(request))

    assert result.ok is True
    assert result.status == 'in_progress'
    assert result.next_action == 'collect_snapshot'
    assert result.run_id
    assert result.continuation_token
    assert result.token_revision == 1


def test_task_checkpoint_continue_rejects_token_conflict():
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    start_result = asyncio.run(
        start_task_with_library(
            StartRequest(
                repo_path='/tmp/repo',
                constitution='Implement only the requested task.',
                project_profile=VALID_PROJECT_PROFILE,
                task={
                    'id': 'task-checkpoint-002',
                    'status': 'pending',
                    'prompt': 'Trigger token conflict',
                    'run_id': None,
                    'commit_message': 'feat: token conflict',
                },
            )
        )
    )

    result = asyncio.run(
        task.resume_task(
            ContinueRequest(
                run_id=start_result.run_id,
                continuation_token='wrong-token',
                idempotency_key='idem-1',
                action_result={
                    'action': 'collect_snapshot',
                    'repo_context': 'snapshot',
                    'workspace_metadata': {
                        'workspace_path': '/tmp/workspace',
                        'source_commit_sha': 'abc123',
                    },
                },
            )
        )
    )

    assert result.ok is False
    assert result.error_code == 'token_conflict'
    assert result.recoverable is True


def test_task_checkpoint_continue_replays_token_conflict_with_same_idempotency_key():
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    start_result = asyncio.run(
        start_task_with_library(
            StartRequest(
                repo_path='/tmp/repo',
                constitution='Implement only the requested task.',
                project_profile=VALID_PROJECT_PROFILE,
                task={
                    'id': 'task-checkpoint-002b',
                    'status': 'pending',
                    'prompt': 'Replay token conflict',
                    'run_id': None,
                    'commit_message': 'feat: token conflict replay',
                },
            )
        )
    )

    request = ContinueRequest(
        run_id=start_result.run_id,
        continuation_token='wrong-token',
        idempotency_key='idem-conflict-replay',
        action_result={
            'action': 'collect_snapshot',
            'repo_context': 'snapshot',
            'workspace_metadata': {
                'workspace_path': '/tmp/workspace',
                'source_commit_sha': 'abc123',
            },
        },
    )

    first = asyncio.run(task.resume_task(request))
    second = asyncio.run(task.resume_task(request))

    assert first.ok is False
    assert first.error_code == 'token_conflict'
    assert first.recoverable is True
    assert first.model_dump() == second.model_dump()


def test_task_checkpoint_continue_rejects_invalid_transition():
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    start_result = asyncio.run(
        start_task_with_library(
            StartRequest(
                repo_path='/tmp/repo',
                constitution='Implement only the requested task.',
                project_profile=VALID_PROJECT_PROFILE,
                task={
                    'id': 'task-checkpoint-002c',
                    'status': 'pending',
                    'prompt': 'Invalid transition',
                    'run_id': None,
                    'commit_message': 'feat: invalid transition',
                },
            )
        )
    )

    result = asyncio.run(
        task.resume_task(
            ContinueRequest(
                run_id=start_result.run_id,
                continuation_token=start_result.continuation_token,
                idempotency_key='idem-invalid-transition',
                action_result={
                    'action': 'commit_if_allowed',
                    'committed': False,
                    'error': 'wrong action for this checkpoint',
                },
            )
        )
    )

    assert result.ok is False
    assert result.error_code == 'invalid_transition'
    assert result.recoverable is True


def test_task_checkpoint_continue_replays_idempotent_response(monkeypatch):
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    execution_plan = ExecutionPlan(
        phase='mvp',
        reasoning='checkpoint test plan',
        generator=GeneratorAssignment(
            persona='tech_lead',
            skills=[],
            focus='ship the change',
        ),
        reviewers=[
            ReviewerAssignment(
                persona='tech_lead',
                skills=['small_patch_quality'],
                strictness=55,
                focus='review the patch',
            )
        ],
    )

    async def fake_create_execution_plan(**_kwargs):
        return execution_plan

    async def fake_call_together(_model, _prompt):
        return {
            'text': '{"operations": []}',
            'input_tokens': 10,
            'output_tokens': 5,
            'duration_ms': 100,
        }

    monkeypatch.setattr(task, 'create_execution_plan', fake_create_execution_plan)
    monkeypatch.setattr(task, 'call_together', fake_call_together)

    start_result = asyncio.run(
        start_task_with_library(
            StartRequest(
                repo_path='/tmp/repo',
                constitution='Implement only the requested task.',
                project_profile=VALID_PROJECT_PROFILE,
                task={
                    'id': 'task-checkpoint-003',
                    'status': 'pending',
                    'prompt': 'Validate idempotent replay',
                    'run_id': None,
                    'commit_message': 'feat: idempotency',
                },
            )
        )
    )

    request = ContinueRequest(
        run_id=start_result.run_id,
        continuation_token=start_result.continuation_token,
        idempotency_key='idem-replay',
        action_result={
            'action': 'collect_snapshot',
            'repo_context': 'snapshot',
            'workspace_metadata': {
                'workspace_path': '/tmp/workspace',
                'source_commit_sha': 'abc123',
            },
        },
    )

    first = asyncio.run(task.resume_task(request))
    second = asyncio.run(task.resume_task(request))

    assert first.ok is True
    assert second.ok is True
    assert first.next_action == 'apply_operations'
    assert second.next_action == 'apply_operations'
    assert first.token_revision == second.token_revision
    assert first.continuation_token == second.continuation_token


def test_task_checkpoint_collect_snapshot_failure_is_terminal(monkeypatch):
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    async def fake_create_execution_plan(**_kwargs):
        raise RuntimeError('planner boom')

    monkeypatch.setattr(task, 'create_execution_plan', fake_create_execution_plan)

    start_result = asyncio.run(
        start_task_with_library(
            StartRequest(
                repo_path='/tmp/repo',
                constitution='Implement only the requested task.',
                project_profile=VALID_PROJECT_PROFILE,
                task={
                    'id': 'task-checkpoint-003b',
                    'status': 'pending',
                    'prompt': 'Trigger planner failure',
                    'run_id': None,
                    'commit_message': 'feat: planner failure handling',
                },
            )
        )
    )

    response = asyncio.run(
        task.resume_task(
            ContinueRequest(
                run_id=start_result.run_id,
                continuation_token=start_result.continuation_token,
                idempotency_key='idem-fail-fast',
                action_result={
                    'action': 'collect_snapshot',
                    'repo_context': 'snapshot',
                    'workspace_metadata': {
                        'workspace_path': '/tmp/workspace',
                        'source_commit_sha': 'abc123',
                    },
                },
            )
        )
    )

    assert response.ok is True
    assert response.status == 'failed'
    assert response.next_action == 'none'
    assert response.continuation_token is None
    assert response.message is not None
    assert 'collect_snapshot' in response.message
    assert 'planner boom' in response.message



def test_task_checkpoint_get_returns_latest_state():
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    start_result = asyncio.run(
        start_task_with_library(
            StartRequest(
                repo_path='/tmp/repo',
                constitution='Implement only the requested task.',
                project_profile=VALID_PROJECT_PROFILE,
                task={
                    'id': 'task-checkpoint-004',
                    'status': 'pending',
                    'prompt': 'Read run state',
                    'run_id': None,
                    'commit_message': 'feat: get state',
                },
            )
        )
    )

    get_result = asyncio.run(task.describe_task(start_result.run_id))

    assert get_result.ok is True
    assert get_result.run_id == start_result.run_id
    assert get_result.next_action == 'collect_snapshot'

    missing_result = asyncio.run(task.describe_task('missing-run-id'))

    assert missing_result.ok is False
    assert missing_result.error_code == 'run_not_found'
