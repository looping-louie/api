import asyncio

from src.app.controllers import workflow
from src.app.controllers import task
from src.app.schemas import (
    ExecutionPlan,
    GeneratorAssignment,
    ReviewerAssignment,
    RunTaskRequest,
    RunWorkflowRequest,
)


def test_workflow_controller_uses_harness_service_path(monkeypatch):
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

    async def fake_create_execution_plan(**_kwargs):
        return execution_plan

    async def fake_run_harness(_req):
        return FakeRunResponse()

    def fake_load_constitution(_repo_path):
        return ''

    def fake_build_project_profile(_repo_path):
        return 'profile'

    def fake_has_changes(_repo_path):
        return True

    def fake_commit_all(*, repo_path, message):
        assert repo_path == '/tmp/repo'
        assert message == 'feat: implement small change'
        return 'sha123'

    monkeypatch.setattr(workflow, 'create_execution_plan', fake_create_execution_plan)
    monkeypatch.setattr(workflow, 'run_harness', fake_run_harness)
    monkeypatch.setattr(workflow, 'load_constitution', fake_load_constitution)
    monkeypatch.setattr(workflow, 'build_project_profile', fake_build_project_profile)
    monkeypatch.setattr(workflow, 'has_changes', fake_has_changes)
    monkeypatch.setattr(workflow, 'commit_all', fake_commit_all)

    request = RunWorkflowRequest(
        repo_path='/tmp/repo',
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
    assert len(result.completed) == 1
    assert result.completed[0].run_id == 'run-123'


def test_task_controller_uses_harness_service_path(monkeypatch):
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

    async def fake_create_execution_plan(**_kwargs):
        return execution_plan

    async def fake_run_harness(_req):
        return FakeRunResponse()

    def fake_load_constitution(_repo_path):
        return ''

    def fake_build_project_profile(_repo_path):
        return 'profile'

    def fake_has_changes(_repo_path):
        return True

    def fake_commit_all(*, repo_path, message):
        assert repo_path == '/tmp/repo'
        assert message == 'feat: implement small change'
        return 'sha456'

    monkeypatch.setattr(task, 'create_execution_plan', fake_create_execution_plan)
    monkeypatch.setattr(task, 'run_harness', fake_run_harness)
    monkeypatch.setattr(task, 'load_constitution', fake_load_constitution)
    monkeypatch.setattr(task, 'build_project_profile', fake_build_project_profile)
    monkeypatch.setattr(task, 'has_changes', fake_has_changes)
    monkeypatch.setattr(task, 'commit_all', fake_commit_all)

    request = RunTaskRequest(
        repo_path='/tmp/repo',
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
    assert result.run_id == 'run-456'
    assert result.completed is not None
    assert result.completed.commit_sha == 'sha456'


def test_task_controller_rejects_non_pending_task(monkeypatch):
    called = False

    async def fake_create_execution_plan(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError('Planner should not be called for non-pending task')

    monkeypatch.setattr(task, 'create_execution_plan', fake_create_execution_plan)

    request = RunTaskRequest(
        repo_path='/tmp/repo',
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


def test_task_controller_stops_when_no_changes(monkeypatch):
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
        run_id = 'run-789'

    async def fake_create_execution_plan(**_kwargs):
        return execution_plan

    async def fake_run_harness(_req):
        return FakeRunResponse()

    def fake_load_constitution(_repo_path):
        return ''

    def fake_build_project_profile(_repo_path):
        return 'profile'

    def fake_has_changes(_repo_path):
        return False

    def fake_commit_all(*, repo_path, message):
        raise AssertionError('commit_all should not be called when no changes')

    monkeypatch.setattr(task, 'create_execution_plan', fake_create_execution_plan)
    monkeypatch.setattr(task, 'run_harness', fake_run_harness)
    monkeypatch.setattr(task, 'load_constitution', fake_load_constitution)
    monkeypatch.setattr(task, 'build_project_profile', fake_build_project_profile)
    monkeypatch.setattr(task, 'has_changes', fake_has_changes)
    monkeypatch.setattr(task, 'commit_all', fake_commit_all)

    request = RunTaskRequest(
        repo_path='/tmp/repo',
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
    assert result.task_id == 'task-003'
    assert result.run_id == 'run-789'
    assert result.approved is True
