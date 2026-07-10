import asyncio

from src.app.controllers import harness_runner, tasks_runner
from src.app.schemas import (
    ExecutionPlan,
    GeneratorAssignment,
    ReviewerAssignment,
    RunHarnessRequest,
    RunTasksRequest,
)


def test_harness_controller_delegates_to_service(monkeypatch):
    captured = {}
    expected_response = {'ok': True}

    async def fake_run_harness_service(req):
        captured['req'] = req
        return expected_response

    monkeypatch.setattr(
        harness_runner,
        'run_harness_service',
        fake_run_harness_service,
    )

    request = RunHarnessRequest(
        prompt='test prompt',
        repo_path='/tmp/repo',
    )

    result = asyncio.run(harness_runner.run_harness(request))

    assert result == expected_response
    assert captured['req'] is request


def test_tasks_runner_uses_harness_service_path(monkeypatch):
    pending_task = {
        'id': 'task-001',
        'status': 'pending',
        'prompt': 'Implement small change',
        'commit_message': 'feat: implement small change',
    }

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

    call_state = {'pending_returned': False, 'marked_done': False}

    def fake_load_constitution(_repo_path):
        return ''

    def fake_build_project_profile(_repo_path):
        return 'profile'

    def fake_load_tasks(_tasks_path):
        return [pending_task]

    def fake_get_next_pending_task(_tasks):
        if not call_state['pending_returned']:
            call_state['pending_returned'] = True
            return pending_task
        return None

    async def fake_create_execution_plan(**_kwargs):
        return execution_plan

    async def fake_run_harness(_req):
        return FakeRunResponse()

    def fake_has_changes(_repo_path):
        return True

    def fake_commit_all(*, repo_path, message):
        assert repo_path == '/tmp/repo'
        assert message == pending_task['commit_message']
        return 'sha123'

    def fake_mark_task_done(_tasks, task_id, run_id):
        call_state['marked_done'] = True
        assert task_id == pending_task['id']
        assert run_id == 'run-123'

    def fake_save_tasks(_tasks_path, _tasks):
        return None

    monkeypatch.setattr(tasks_runner, 'load_constitution', fake_load_constitution)
    monkeypatch.setattr(
        tasks_runner,
        'build_project_profile',
        fake_build_project_profile,
    )
    monkeypatch.setattr(tasks_runner, 'load_tasks', fake_load_tasks)
    monkeypatch.setattr(
        tasks_runner,
        'get_next_pending_task',
        fake_get_next_pending_task,
    )
    monkeypatch.setattr(
        tasks_runner,
        'create_execution_plan',
        fake_create_execution_plan,
    )
    monkeypatch.setattr(tasks_runner, 'run_harness', fake_run_harness)
    monkeypatch.setattr(tasks_runner, 'has_changes', fake_has_changes)
    monkeypatch.setattr(tasks_runner, 'commit_all', fake_commit_all)
    monkeypatch.setattr(tasks_runner, 'mark_task_done', fake_mark_task_done)
    monkeypatch.setattr(tasks_runner, 'save_tasks', fake_save_tasks)

    request = RunTasksRequest(
        repo_path='/tmp/repo',
        tasks_path='/tmp/tasks.json',
    )

    result = asyncio.run(tasks_runner.run_tasks(request))

    assert result['ok'] is True
    assert result['status'] == 'completed'
    assert len(result['completed']) == 1
    assert result['completed'][0]['run_id'] == 'run-123'
    assert call_state['marked_done'] is True
