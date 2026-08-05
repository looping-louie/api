"""HTTP contract tests for loop routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.loop import LoopController
from src.app.controllers.loop_run import LoopRunController
from src.app.catalogs.providers import ProviderId
from src.app.models.loop_run import LoopRunDocument
from src.app.routers.loops import router as loops_router
from src.app.services.model_execution import (
    ModelExecutionError,
    ModelExecutionResult,
)
from src.app.services.loop_runs.service import LoopRunService
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant import TenantService
from src.app.utils.http import register_exception_handlers
from tests.fakes.loop_repository import FakeLoopRepository
from tests.fakes.reference_repository import FakeReferenceRepository
from tests.services.test_loop_service import build_service, seed_references


class FakeLoopRunRepository:
    """Store loop runs in memory for HTTP contract tests."""

    def __init__(self) -> None:
        """Initialize the empty in-memory run collection."""

        self.documents: dict[str, LoopRunDocument] = {}
        self.idempotency_responses: dict[
            tuple[str, str], LoopRunDocument
        ] = {}

    async def create(
        self,
        *,
        document: LoopRunDocument,
    ) -> LoopRunDocument:
        """Store one created run."""

        self.documents[document.id] = document
        return document

    async def has_runs(
        self,
        *,
        workspace_id: str,
        loop_id: str,
    ) -> bool:
        """Return whether the selected loop has an in-memory run."""

        return any(
            document.workspace_id == workspace_id and document.loop_id == loop_id
            for document in self.documents.values()
        )

    async def get(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
    ) -> LoopRunDocument | None:
        """Return a run only beneath its matching loop and workspace."""

        document = self.documents.get(run_id)
        if (
            document is None
            or document.workspace_id != workspace_id
            or document.loop_id != loop_id
        ):
            return None
        return document

    async def list(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[LoopRunDocument], int]:
        """Return one newest-first page of matching in-memory records."""

        documents = [
            document
            for document in self.documents.values()
            if (
                document.workspace_id == workspace_id
                and document.loop_id == loop_id
            )
        ]
        documents.sort(key=lambda document: document.created_at, reverse=True)
        return documents[offset : offset + limit], len(documents)

    async def continue_collect_snapshot(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        execution_context: dict[str, object],
        updated_at: datetime,
    ) -> LoopRunDocument:
        """Advance one initial snapshot transition with replay protection."""

        replay_key = (run_id, idempotency_key)
        replay = self.idempotency_responses.get(replay_key)
        if replay is not None:
            return replay

        document = await self.get(
            workspace_id=workspace_id,
            loop_id=loop_id,
            run_id=run_id,
        )
        assert document is not None
        assert document.continuation_token == continuation_token
        updated = LoopRunDocument(
            id=document.id,
            workspace_id=document.workspace_id,
            loop_id=document.loop_id,
            input=document.input,
            status=document.status,
            state='awaiting_generation',
            next_action='none',
            iteration=document.iteration,
            token_revision=document.token_revision + 1,
            continuation_token=None,
            loop_snapshot=document.loop_snapshot,
            execution_context=execution_context,
            created_at=document.created_at,
            created_by=document.created_by,
            updated_at=updated_at,
        )
        self.documents[run_id] = updated
        self.idempotency_responses[replay_key] = updated
        return updated

    async def transition(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        expected_action: str,
        status: str,
        state: str,
        next_action: str,
        next_continuation_token: str | None,
        execution_context: dict[str, object],
        updated_at: datetime,
        iteration: int | None = None,
    ) -> LoopRunDocument:
        """Persist one generic checkpoint transition for route contracts."""

        replay_key = (run_id, idempotency_key)
        replay = self.idempotency_responses.get(replay_key)
        if replay is not None:
            return replay
        document = await self.get(
            workspace_id=workspace_id,
            loop_id=loop_id,
            run_id=run_id,
        )
        assert document is not None
        assert document.continuation_token == continuation_token
        assert document.next_action == expected_action
        updated = LoopRunDocument(
            id=document.id,
            workspace_id=document.workspace_id,
            loop_id=document.loop_id,
            input=document.input,
            status=status,
            state=state,
            next_action=next_action,
            iteration=iteration if iteration is not None else document.iteration,
            token_revision=document.token_revision + 1,
            continuation_token=next_continuation_token,
            loop_snapshot=document.loop_snapshot,
            execution_context=execution_context,
            created_at=document.created_at,
            created_by=document.created_by,
            updated_at=updated_at,
        )
        self.documents[run_id] = updated
        self.idempotency_responses[replay_key] = updated
        return updated


class FakeModelExecutionService:
    """Return deterministic direct and roundtable model responses."""

    def __init__(self, *, review_approved: bool = True) -> None:
        """Store prompts received during a route test."""

        self.prompts: list[str] = []
        self.review_approved = review_approved

    async def execute(
        self,
        *,
        workspace_id: str,
        model_id: str,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> ModelExecutionResult:
        """Return stage-specific JSON without contacting a provider."""

        assert workspace_id == 'workspace-1'
        assert model_id == 'model-1'
        assert 'Repository context.' in prompt
        assert system_prompt is None
        assert json_mode is True
        self.prompts.append(prompt)
        if 'Propose a solution' in prompt:
            text = '{"proposal":"candidate solution"}'
        elif 'JSON object critiquing these candidate proposals' in prompt:
            text = '{"critique":"address the main risk"}'
        elif 'approved boolean and feedback string' in prompt:
            text = (
                '{"approved":true,"feedback":"Approved."}'
                if self.review_approved
                else '{"approved":false,"feedback":"Add missing detail."}'
            )
        else:
            text = (
                '{"operations":[{"operation":"create",'
                '"path":"output.txt","content":"created"}],'
                '"commit_message":"feat: create output"}'
            )
        return ModelExecutionResult(
            text=text,
            provider_id=ProviderId.OPENAI,
            model_id=model_id,
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


class FakeInstructionLibraryService:
    """Resolve deterministic persona content for loop-run route tests."""

    async def load(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
    ) -> 'FakeInstructionLibraryService':
        """Return this library for the authenticated workspace."""

        assert user_id == 'user-1'
        assert requested_workspace_id is None
        return self

    @staticmethod
    def persona_content(persona_id: str) -> str:
        """Return deterministic content for the configured test persona."""

        assert persona_id == 'persona-1'
        return 'Use this assigned persona.'


class FailingModelExecutionService:
    """Raise a deterministic model execution failure for route coverage."""

    async def execute(
        self,
        **_: object,
    ) -> ModelExecutionResult:
        """Simulate an unavailable completion provider."""

        raise ModelExecutionError('Model provider returned HTTP 503.')


def build_app(
    *,
    controller: LoopController,
    loop_run_controller: LoopRunController,
) -> FastAPI:
    """Build an authenticated minimal loop application."""

    app = FastAPI()
    app.state.loop_controller = controller
    app.state.loop_run_controller = loop_run_controller

    @app.middleware("http")
    async def add_authenticated_user(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Inject the actor required by route dependencies."""

        request.state.user_id = "user-1"
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(loops_router, prefix="/api/v1")
    return app


def build_client(
    *,
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
    repository: FakeLoopRepository | None = None,
    model_execution_service: FakeModelExecutionService | None = None,
    instruction_library_service: FakeInstructionLibraryService | None = None,
) -> TestClient:
    """Build a client backed by deterministic in-memory dependencies."""

    seed_references(reference_repository)
    run_repository = FakeLoopRunRepository()
    service = build_service(
        repository=repository or FakeLoopRepository(),
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
        loop_run_repository=run_repository,
    )
    run_service = LoopRunService(
        repository=run_repository,
        loop_service=service,
        tenant_service=tenant_service,
        id_factory=lambda: 'loop-run-1',
        clock=lambda: datetime(2026, 8, 3, tzinfo=UTC),
        model_execution_service=model_execution_service,
        instruction_library_service=instruction_library_service,
    )
    return TestClient(
        build_app(
            controller=LoopController(loop_service=service),
            loop_run_controller=LoopRunController(
                loop_run_service=run_service,
            ),
        )
    )


def direct_payload(*, title: str = "Direct loop") -> dict[str, object]:
    """Return one valid direct-flow request body."""

    return {
        "title": title,
        "description": "Produce one answer.",
        "flow": "direct",
        "stop_conditions": {"max_tokens": 5000},
        "agents": [
            {
                "model_id": "model-1",
                "persona_id": "persona-1",
                "role": "generator",
            }
        ],
        "output_contract": {
            "type": "text",
            "description": "Human-readable answer.",
        },
    }


def roundtable_payload() -> dict[str, object]:
    """Return one valid roundtable request body."""

    return {
        'title': 'Roundtable loop',
        'description': 'Synthesize competing proposals.',
        'flow': 'roundtable',
        'stop_conditions': {'max_tokens': 5000},
        'agents': [
            {
                'model_id': 'model-1',
                'persona_id': 'persona-1',
                'role': 'generator',
            },
            {
                'model_id': 'model-1',
                'persona_id': 'persona-1',
                'role': 'generator',
            },
            {
                'model_id': 'model-1',
                'persona_id': 'persona-1',
                'role': 'reviewer',
            },
            {
                'model_id': 'model-1',
                'persona_id': 'persona-1',
                'role': 'aggregator',
            },
        ],
        'output_contract': {
            'type': 'files',
            'description': 'Create one output file.',
            'files': ['output.txt'],
        },
    }


def test_loop_rest_crud_and_changelog_routes(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Create, list, get, patch, audit, and delete use REST paths."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    created_response = client.post(
        "/api/v1/loops",
        json=direct_payload(),
    )
    assert created_response.status_code == 201
    created = created_response.json()
    loop_id = created["id"]
    assert created["status"] == "active"
    assert created["created_by"] == "user-1"
    assert created["agents"][0]["id"]
    assert "skill_ids" not in created["agents"][0]

    listed = client.get("/api/v1/loops?offset=0")
    fetched = client.get(f"/api/v1/loops/{loop_id}")
    patched = client.patch(
        f"/api/v1/loops/{loop_id}",
        json={"description": "Updated answer."},
    )
    changelog = client.get(
        f"/api/v1/loops/{loop_id}/changelog"
    )
    deleted = client.delete(f"/api/v1/loops/{loop_id}")
    retained = client.get(
        f"/api/v1/loops/{loop_id}/changelog"
    )

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert fetched.json()["title"] == "Direct loop"
    assert patched.json()["description"] == "Updated answer."
    assert changelog.json()["items"][0]["change_type"] == "updated"
    assert all(
        item["actor_id"] == "user-1"
        for item in changelog.json()["items"]
    )
    assert changelog.json()["items"][0]["diff"] == {
        "description": {
            "from": "Produce one answer.",
            "to": "Updated answer.",
        }
    }
    assert deleted.json() == {"deleted": True}
    assert retained.status_code == 200
    assert retained.json()["items"][0]["change_type"] == "deleted"
    assert retained.json()["items"][0]["actor_id"] == "user-1"
    assert client.get(f"/api/v1/loops/{loop_id}").status_code == 404


def test_loop_listing_uses_fixed_ten_item_pages(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Offset advances through a collection whose page size is always ten."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    for position in range(12):
        response = client.post(
            "/api/v1/loops",
            json=direct_payload(title=f"Loop {position:02d}"),
        )
        assert response.status_code == 201

    first = client.get("/api/v1/loops")
    second = client.get("/api/v1/loops?offset=10")

    assert first.json()["total"] == 12
    assert len(first.json()["items"]) == 10
    assert second.json()["total"] == 12
    assert len(second.json()["items"]) == 2


def test_loop_run_routes_create_list_and_describe_runs(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Runs are created and read beneath their active parent loop."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    loop_id = client.post('/api/v1/loops', json=direct_payload()).json()['id']

    created = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Improve API error messages.'},
    )
    run_id = created.json()['id']
    listed = client.get(f'/api/v1/loops/{loop_id}/runs')
    described = client.get(f'/api/v1/loops/{loop_id}/runs/{run_id}')

    assert created.status_code == 201
    assert created.json()['loop_id'] == loop_id
    assert created.json()['state'] == 'awaiting_snapshot'
    assert created.json()['next_action'] == 'collect_snapshot'
    assert created.json()['token_revision'] == 0
    assert listed.json()['total'] == 1
    assert listed.json()['items'][0]['id'] == run_id
    assert described.json()['input'] == 'Improve API error messages.'


def test_loop_run_routes_reject_inactive_or_unknown_parents(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Only active, workspace-visible loops may create new runs."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    loop_id = client.post('/api/v1/loops', json=direct_payload()).json()['id']
    client.patch(f'/api/v1/loops/{loop_id}', json={'status': 'disabled'})

    disabled = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Do not run.'},
    )
    unknown = client.post(
        '/api/v1/loops/unknown/runs',
        json={'input': 'Do not run.'},
    )
    blank = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': '   '},
    )

    assert disabled.status_code == 409
    assert unknown.status_code == 404
    assert blank.status_code == 422


def test_loop_run_snapshot_continuation_accepts_only_cli_context(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """A snapshot continuation advances the run without accepting repo paths."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    loop_id = client.post('/api/v1/loops', json=direct_payload()).json()['id']
    created = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Improve validation errors.'},
    ).json()
    payload = {
        'continuation_token': created['continuation_token'],
        'idempotency_key': 'snapshot-1',
        'result': {
            'action': 'collect_snapshot',
            'repo_context': 'Repository context.',
            'workspace_metadata': {
                'workspace_path': '/workspace/project',
                'source_commit_sha': 'abc123',
            },
            'constitution': 'Keep changes small.',
            'project_profile': {
                'source_file_count': 1,
                'approximate_source_chars': 42,
                'extension_counts': {'.py': 1},
                'top_level_entries': ['src'],
                'markers': {
                    'nuxt': False,
                    'package_json': False,
                    'fastapi': True,
                    'docker': False,
                    'tests': True,
                },
            },
        },
    }

    continued = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json=payload,
    )
    invalid = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json={**payload, 'repo_path': '/workspace/project'},
    )

    assert continued.status_code == 200
    assert continued.json()['state'] == 'awaiting_generation'
    assert continued.json()['next_action'] == 'none'
    assert continued.json()['continuation_token'] is None
    assert continued.json()['token_revision'] == 1
    assert invalid.status_code == 422


def test_direct_loop_run_generates_applies_and_commits(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """A direct generator loop reaches commit handoff through checkpoints."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
        model_execution_service=FakeModelExecutionService(),
    )
    loop_id = client.post('/api/v1/loops', json=direct_payload()).json()['id']
    created = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Create an output file.'},
    ).json()
    snapshot_response = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json=_snapshot_payload(created['continuation_token']),
    )
    assert snapshot_response.status_code == 200, snapshot_response.json()
    snapshot = snapshot_response.json()
    applied = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json={
            'continuation_token': snapshot['continuation_token'],
            'idempotency_key': 'apply-1',
            'result': {'action': 'apply_operations', 'applied': True},
        },
    ).json()
    completed = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json={
            'continuation_token': applied['continuation_token'],
            'idempotency_key': 'commit-1',
            'result': {
                'action': 'commit_if_allowed',
                'committed': True,
                'commit_sha': 'abc123',
                'commit_message': 'feat: create output',
            },
        },
    )

    assert snapshot['state'] == 'awaiting_apply'
    assert snapshot['next_action'] == 'apply_operations'
    assert snapshot['payload']['operations'][0]['path'] == 'output.txt'
    assert applied['state'] == 'awaiting_commit'
    assert applied['next_action'] == 'commit_if_allowed'
    assert completed.json()['status'] == 'completed'
    assert completed.json()['next_action'] == 'none'


def test_roundtable_loop_aggregates_proposals_and_critique(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """A roundtable sends final aggregated operations to the CLI checkpoint."""

    model_execution_service = FakeModelExecutionService()
    instruction_library_service = FakeInstructionLibraryService()
    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
        model_execution_service=model_execution_service,
        instruction_library_service=instruction_library_service,
    )
    loop_id = client.post('/api/v1/loops', json=roundtable_payload()).json()['id']
    created = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Create an output file.'},
    ).json()
    response = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json=_snapshot_payload(created['continuation_token']),
    )

    assert response.status_code == 200, response.json()
    assert response.json()['next_action'] == 'apply_operations'
    assert response.json()['payload']['operations'][0]['path'] == 'output.txt'
    assert len(model_execution_service.prompts) == 4
    assert all(
        'JSON object proposing a solution' in prompt
        for prompt in model_execution_service.prompts[:2]
    )
    assert (
        'JSON object critiquing these candidate proposals'
        in model_execution_service.prompts[2]
    )
    assert 'Generator proposals' in model_execution_service.prompts[3]
    assert 'Reviewer critique' in model_execution_service.prompts[3]
    assert 'output.txt' in model_execution_service.prompts[3]
    assert all(
        prompt.startswith('Persona instructions:\nUse this assigned persona.')
        for prompt in model_execution_service.prompts
    )


def test_roundtable_loop_reviews_applied_changes_before_commit(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """A reviewer-configured loop requires post-apply approval before commit."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
        model_execution_service=FakeModelExecutionService(),
    )
    loop_id = client.post('/api/v1/loops', json=roundtable_payload()).json()['id']
    created = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Create an output file.'},
    ).json()
    snapshot = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json=_snapshot_payload(created['continuation_token']),
    ).json()
    applied = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json={
            'continuation_token': snapshot['continuation_token'],
            'idempotency_key': 'apply-1',
            'result': {'action': 'apply_operations', 'applied': True},
        },
    ).json()
    reviewed = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json={
            'continuation_token': applied['continuation_token'],
            'idempotency_key': 'review-1',
            'result': {
                'action': 'submit_review_input',
                'final_diff': 'diff --git a/output.txt b/output.txt',
                'changed_file_contents': {'output.txt': 'created'},
            },
        },
    ).json()

    assert applied['next_action'] == 'submit_review_input'
    assert reviewed['state'] == 'awaiting_commit'
    assert reviewed['next_action'] == 'commit_if_allowed'


def test_roundtable_loop_retries_after_reviewer_rejection(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """A rejected review starts the next persisted loop iteration."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
        model_execution_service=FakeModelExecutionService(review_approved=False),
    )
    payload = roundtable_payload()
    payload['stop_conditions']['max_iterations'] = 3
    loop_id = client.post('/api/v1/loops', json=payload).json()['id']
    created = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Create an output file.'},
    ).json()
    snapshot = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json=_snapshot_payload(created['continuation_token']),
    ).json()
    applied = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json={
            'continuation_token': snapshot['continuation_token'],
            'idempotency_key': 'apply-1',
            'result': {'action': 'apply_operations', 'applied': True},
        },
    ).json()
    reviewed = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json={
            'continuation_token': applied['continuation_token'],
            'idempotency_key': 'review-1',
            'result': {
                'action': 'submit_review_input',
                'final_diff': 'diff --git a/output.txt b/output.txt',
                'changed_file_contents': {'output.txt': 'created'},
            },
        },
    ).json()

    assert reviewed['state'] == 'awaiting_snapshot'
    assert reviewed['next_action'] == 'collect_snapshot'
    assert reviewed['iteration'] == 2


def test_loop_run_returns_structured_model_execution_error(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """A provider failure does not escape as an opaque internal error."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
        model_execution_service=FailingModelExecutionService(),
    )
    loop_id = client.post('/api/v1/loops', json=direct_payload()).json()['id']
    created = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Create an output file.'},
    ).json()
    response = client.post(
        f'/api/v1/loops/{loop_id}/runs/{created["id"]}/continue',
        json=_snapshot_payload(created['continuation_token']),
    )

    assert response.status_code == 502
    assert response.json()['error']['code'] == 'model_execution_error'


def _snapshot_payload(continuation_token: str) -> dict[str, object]:
    """Build the standard direct-loop snapshot continuation request."""

    return {
        'continuation_token': continuation_token,
        'idempotency_key': 'snapshot-1',
        'result': {
            'action': 'collect_snapshot',
            'repo_context': 'Repository context.',
            'workspace_metadata': {
                'workspace_path': '/workspace/project',
                'source_commit_sha': 'abc123',
            },
            'constitution': 'Keep changes small.',
            'project_profile': {
                'source_file_count': 1,
                'approximate_source_chars': 42,
                'extension_counts': {'.py': 1},
                'top_level_entries': ['src'],
                'markers': {
                    'nuxt': False,
                    'package_json': False,
                    'fastapi': True,
                    'docker': False,
                    'tests': True,
                },
            },
        },
    }


def test_deleting_loop_with_runs_archives_its_definition(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """A loop with retained executions remains available as archived history."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    loop_id = client.post('/api/v1/loops', json=direct_payload()).json()['id']
    run_id = client.post(
        f'/api/v1/loops/{loop_id}/runs',
        json={'input': 'Preserve this execution.'},
    ).json()['id']

    deleted = client.delete(f'/api/v1/loops/{loop_id}')
    archived = client.get(f'/api/v1/loops/{loop_id}')
    retained_run = client.get(f'/api/v1/loops/{loop_id}/runs/{run_id}')

    assert deleted.status_code == 200
    assert archived.json()['status'] == 'archived'
    assert retained_run.status_code == 200


def test_loop_payload_rejects_skills_and_invalid_contracts(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Strict write schemas reject skills and incomplete fields."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    with_skills = direct_payload()
    with_skills["agents"][0]["skill_ids"] = ["skill-1"]
    invalid_json = direct_payload()
    invalid_json["output_contract"] = {
        "type": "json",
        "description": "JSON answer.",
    }
    invalid_files = direct_payload()
    invalid_files["output_contract"] = {
        "type": "files",
        "description": "File answer.",
    }
    missing_stops = direct_payload()
    missing_stops["stop_conditions"] = {}
    negative_stops = direct_payload()
    negative_stops["stop_conditions"] = {"max_iterations": -1}
    invalid_flow = direct_payload()
    invalid_flow["flow"] = "pipeline"
    invalid_role = direct_payload()
    invalid_role["agents"][0]["role"] = "chair"

    for payload in (
        with_skills,
        invalid_json,
        invalid_files,
        missing_stops,
        negative_stops,
        invalid_flow,
        invalid_role,
    ):
        assert client.post("/api/v1/loops", json=payload).status_code == 422


def test_patch_rejects_empty_noop_and_immutable_fields(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """PATCH accepts only effective mutable changes."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    loop_id = client.post(
        "/api/v1/loops",
        json=direct_payload(),
    ).json()["id"]

    assert client.patch(
        f"/api/v1/loops/{loop_id}", json={}
    ).status_code == 422
    assert client.patch(
        f"/api/v1/loops/{loop_id}",
        json={"title": "Direct loop"},
    ).status_code == 422
    assert client.patch(
        f"/api/v1/loops/{loop_id}",
        json={"created_by": "forged"},
    ).status_code == 422
    assert client.get(
        "/api/v1/loops/unknown/changelog"
    ).status_code == 404


def test_only_new_loop_routes_are_published(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """OpenAPI publishes only the new loop resource endpoints."""

    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
        reference_resolver=reference_resolver,
    )
    paths = set(client.get("/openapi.json").json()["paths"])

    assert paths == {
        "/api/v1/loops",
        "/api/v1/loops/{loop_id}",
        "/api/v1/loops/{loop_id}/changelog",
        "/api/v1/loops/{loop_id}/runs",
        "/api/v1/loops/{loop_id}/runs/{run_id}",
        "/api/v1/loops/{loop_id}/runs/{run_id}/continue",
    }
