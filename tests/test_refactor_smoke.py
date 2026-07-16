import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.app.controllers import workflow
from src.app.controllers import task
import src.app.services.harness.runner as harness_runner
from src.app.schemas import (
    ExecutionPlan,
    GeneratorAssignment,
    ReviewerAssignment,
    RunTaskRequest,
    RunWorkflowRequest,
)
from src.app.schemas.task import ContinueRequest, StartRequest


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


def _fake_execution_ports(run_id: str = 'run-test'):
    workspace = SimpleNamespace(
        create_workspace=lambda _repo_path: SimpleNamespace(
            run_id=run_id,
            worktree_path=Path('/tmp/worktree'),
        ),
        cleanup_workspace=lambda _workspace: None,
    )
    git = SimpleNamespace(
        validate_patch=lambda _repo_path, _patch: (True, ''),
        apply_patch=lambda _repo_path, _patch: (True, ''),
    )
    return SimpleNamespace(workspace=workspace, git=git)


def test_workflow_controller_uses_harness_service_path(monkeypatch, tmp_path):
    execution_plan = ExecutionPlan(
        phase='mvp',
        reasoning='test plan',
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

    class FakeRunResponse:
        approved = True
        run_id = 'run-123'
        final_output = ''
        execution_trace = []

        class run_metrics:  # pylint: disable=too-few-public-methods,invalid-name
            @staticmethod
            def model_dump():
                return {'iterations': 0}

        @staticmethod
        def model_dump():
            return {
                'run_id': 'run-123',
                'approved': True,
                'final_output': '',
                'execution_trace': [],
                'run_metrics': {'iterations': 0},
            }

    async def fake_create_execution_plan(**_kwargs):
        return execution_plan

    async def fake_run_harness(_req, **_kwargs):
        return FakeRunResponse()

    monkeypatch.setattr(workflow, 'create_execution_plan', fake_create_execution_plan)
    monkeypatch.setattr(workflow, 'run_harness', fake_run_harness)
    monkeypatch.setattr(
        workflow,
        'build_local_harness_execution_ports',
        lambda: _fake_execution_ports('run-123'),
    )
    monkeypatch.setattr(
        workflow,
        'create_workspace',
        lambda _repo_path, _run_id: SimpleNamespace(
            worktree_path=Path('/tmp/worktree'),
        ),
    )
    monkeypatch.setattr(workflow, 'cleanup_workspace', lambda _workspace: None)
    monkeypatch.setattr(
        workflow,
        'build_execution_run_path',
        lambda run_id: tmp_path / run_id,
    )

    request = RunWorkflowRequest(
        repo_path='/tmp/repo',
        constitution='Implement only the requested task.',
        project_profile=VALID_PROJECT_PROFILE,
        tasks=[
            {
                'id': 'task-001',
                'status': 'pending',
                'prompt': 'Implement small change',
                'run_id': None,
                'commit_message': 'feat: implement small change',
            }
        ],
    )

    result = asyncio.run(workflow.run_workflow(request))

    assert result.ok is True
    assert result.status == 'completed'
    assert result.commit_allowed is True
    assert result.task_id == 'task-001'
    assert result.run_id == 'run-123'
    assert len(result.completed) == 1
    assert result.completed[0].run_id == 'run-123'
    assert result.completed[0].commit_sha == 'deprecated API response field'


def test_task_controller_uses_harness_service_path(monkeypatch, tmp_path):
    execution_plan = ExecutionPlan(
        phase='mvp',
        reasoning='test plan',
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

    class FakeRunResponse:
        approved = True
        run_id = 'run-456'
        final_output = ''
        execution_trace = []

        class run_metrics:  # pylint: disable=too-few-public-methods,invalid-name
            @staticmethod
            def model_dump():
                return {'iterations': 0}

        @staticmethod
        def model_dump():
            return {
                'run_id': 'run-456',
                'approved': True,
                'final_output': '',
                'execution_trace': [],
                'run_metrics': {'iterations': 0},
            }

    async def fake_create_execution_plan(**_kwargs):
        return execution_plan

    async def fake_run_harness(_req, **_kwargs):
        return FakeRunResponse()

    monkeypatch.setattr(task, 'create_execution_plan', fake_create_execution_plan)
    monkeypatch.setattr(task, 'run_harness', fake_run_harness)
    monkeypatch.setattr(
        task,
        'build_local_harness_execution_ports',
        lambda: _fake_execution_ports('run-456'),
    )
    monkeypatch.setattr(
        task,
        'create_workspace',
        lambda _repo_path, _run_id: SimpleNamespace(
            worktree_path=Path('/tmp/worktree'),
        ),
    )
    monkeypatch.setattr(task, 'cleanup_workspace', lambda _workspace: None)
    monkeypatch.setattr(
        task,
        'build_execution_run_path',
        lambda run_id: tmp_path / run_id,
    )

    request = RunTaskRequest(
        repo_path='/tmp/repo',
        constitution='Implement only the requested task.',
        project_profile=VALID_PROJECT_PROFILE,
        task={
            'id': 'task-001',
            'status': 'pending',
            'prompt': 'Implement small change',
            'run_id': None,
            'commit_message': 'feat: implement small change',
        },
    )

    result = asyncio.run(task.run_task(request))

    assert result.ok is True
    assert result.status == 'completed'
    assert result.commit_allowed is True
    assert result.run_id == 'run-456'
    assert result.completed is not None
    assert result.completed.commit_sha == 'deprecated API response field'


def test_task_controller_rejects_non_pending_task(monkeypatch):
    called = False

    async def fake_create_execution_plan(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError('Planner should not be called for non-pending task')

    monkeypatch.setattr(task, 'create_execution_plan', fake_create_execution_plan)

    request = RunTaskRequest(
        repo_path='/tmp/repo',
        constitution='Implement only the requested task.',
        project_profile=VALID_PROJECT_PROFILE,
        task={
            'id': 'task-002',
            'status': 'done',
            'prompt': 'Already done',
            'run_id': 'run-old',
            'commit_message': 'feat: no-op',
        },
    )

    result = asyncio.run(task.run_task(request))

    assert called is False
    assert result.ok is False
    assert result.status == 'stopped'
    assert result.task_id == 'task-002'
    assert result.message == 'Task status must be pending to run.'


def test_task_controller_stops_when_not_approved(monkeypatch, tmp_path):
    execution_plan = ExecutionPlan(
        phase='mvp',
        reasoning='test plan',
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

    class FakeRunResponse:
        approved = False
        run_id = 'run-789'
        final_output = ''
        execution_trace = []

        class run_metrics:  # pylint: disable=too-few-public-methods,invalid-name
            @staticmethod
            def model_dump():
                return {'iterations': 0}

        @staticmethod
        def model_dump():
            return {
                'run_id': 'run-789',
                'approved': False,
                'final_output': '',
                'execution_trace': [],
                'run_metrics': {'iterations': 0},
            }

    async def fake_create_execution_plan(**_kwargs):
        return execution_plan

    async def fake_run_harness(_req, **_kwargs):
        return FakeRunResponse()

    monkeypatch.setattr(task, 'create_execution_plan', fake_create_execution_plan)
    monkeypatch.setattr(task, 'run_harness', fake_run_harness)
    monkeypatch.setattr(
        task,
        'build_local_harness_execution_ports',
        lambda: _fake_execution_ports('run-789'),
    )
    monkeypatch.setattr(
        task,
        'create_workspace',
        lambda _repo_path, _run_id: SimpleNamespace(
            worktree_path=Path('/tmp/worktree'),
        ),
    )
    monkeypatch.setattr(task, 'cleanup_workspace', lambda _workspace: None)
    monkeypatch.setattr(
        task,
        'build_execution_run_path',
        lambda run_id: tmp_path / run_id,
    )

    request = RunTaskRequest(
        repo_path='/tmp/repo',
        constitution='Implement only the requested task.',
        project_profile=VALID_PROJECT_PROFILE,
        task={
            'id': 'task-003',
            'status': 'pending',
            'prompt': 'Implement small change',
            'run_id': None,
            'commit_message': 'feat: implement small change',
        },
    )

    result = asyncio.run(task.run_task(request))

    assert result.ok is False
    assert result.status == 'stopped'
    assert result.commit_allowed is False
    assert result.task_id == 'task-003'
    assert result.run_id == 'run-789'
    assert result.approved is False


def test_request_schema_rejects_invalid_project_profile():
    with pytest.raises(ValueError):
        RunTaskRequest(
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

    result = asyncio.run(task.start_task(request))

    assert result.ok is True
    assert result.status == 'in_progress'
    assert result.next_action == 'collect_snapshot'
    assert result.run_id
    assert result.continuation_token
    assert result.token_revision == 1


def test_task_checkpoint_continue_rejects_token_conflict():
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    start_result = asyncio.run(
        task.start_task(
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
        task.continue_task(
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
        task.start_task(
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

    first = asyncio.run(task.continue_task(request))
    second = asyncio.run(task.continue_task(request))

    assert first.ok is True
    assert second.ok is True
    assert first.next_action == 'apply_operations'
    assert second.next_action == 'apply_operations'
    assert first.token_revision == second.token_revision
    assert first.continuation_token == second.continuation_token



def test_task_checkpoint_get_returns_latest_state():
    task._TASK_RUNS.clear()  # pylint: disable=protected-access

    start_result = asyncio.run(
        task.start_task(
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

    get_result = asyncio.run(task.get_task(start_result.run_id))

    assert get_result.ok is True
    assert get_result.run_id == start_result.run_id
    assert get_result.next_action == 'collect_snapshot'

    missing_result = asyncio.run(task.get_task('missing-run-id'))

    assert missing_result.ok is False
    assert missing_result.error_code == 'run_not_found'

    with pytest.raises(ValueError):
        RunWorkflowRequest(
            repo_path='/tmp/repo',
            constitution='Implement only the requested task.',
            project_profile={
                'source_file_count': 12,
                'approximate_source_chars': 2048,
                'extension_counts': {'.py': 10},
                'top_level_entries': ['src/'],
                # Missing required markers payload
            },
            tasks=[
                {
                    'id': 'task-005',
                    'status': 'pending',
                    'prompt': 'Implement another change',
                    'run_id': None,
                    'commit_message': 'feat: implement another change',
                }
            ],
        )


def test_harness_runner_creates_execution_run_path_under_runtime(
    monkeypatch,
    tmp_path,
):
    executions_root = tmp_path / 'runtime' / 'executions'
    monkeypatch.setattr(harness_runner, 'EXECUTION_RUNS_DIR', executions_root)

    run_path = harness_runner.build_execution_run_path('run-abc123')

    assert run_path == executions_root / 'run-abc123'
    assert run_path.exists()
    assert run_path.is_dir()
