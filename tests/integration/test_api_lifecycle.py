"""HTTP integration coverage for the composed API resource lifecycle."""

from __future__ import annotations

from fastapi.testclient import TestClient
from httpx import Response


def test_composed_api_supports_resource_and_worker_lifecycles(
    api_client: TestClient,
) -> None:
    """Exercise persistent resources and a claimable Pipeline run end to end."""

    _assert_success(api_client.get('/api/v1/catalog/providers'))
    _assert_success(api_client.get('/api/v1/catalog/models'))
    _assert_success(api_client.get('/api/v1/catalog/personas'))
    _assert_success(api_client.get('/api/v1/catalog/skills'))
    _assert_success(api_client.get('/api/v1/users/me'))
    _assert_success(
        api_client.patch(
            '/api/v1/users/me',
            json={'default_harness': None},
        )
    )

    project = _create_project(api_client, 'Integration Project')
    project_id = project['id']
    project_headers = {'X-Project-ID': project_id}
    _assert_success(api_client.get('/api/v1/projects'))
    _assert_success(api_client.get(f'/api/v1/projects/{project_id}'))
    updated_project = api_client.patch(
        f'/api/v1/projects/{project_id}',
        json={'name': 'Updated integration project'},
    )
    _assert_success(updated_project)
    assert updated_project.json()['name'] == 'Updated integration project'

    linked_service = api_client.post(
        '/api/v1/linked-services',
        json={
            'name': 'integration_together',
            'provider_type': 'together',
            'config': {
                'api_key': 'integration-test-key',
                'base_url': 'https://provider.example.test/v1',
            },
        },
    )
    _assert_created(linked_service)
    linked_service_id = linked_service.json()['id']
    _assert_success(
        api_client.get(f'/api/v1/linked-services/{linked_service_id}')
    )
    _assert_success(api_client.get('/api/v1/linked-services'))

    models = api_client.get(
        '/api/v1/users/me/models?provider_id=together&available=true'
    )
    _assert_success(models)
    model_id = models.json()['items'][0]['id']
    _assert_success(api_client.get(f'/api/v1/users/me/models/{model_id}'))

    skill = api_client.post('/api/v1/skills', json=_skill_payload())
    _assert_created(skill)
    skill_id = skill.json()['id']
    _assert_success(api_client.get(f'/api/v1/skills/{skill_id}'))
    _assert_success(api_client.get('/api/v1/skills'))
    updated_skill = api_client.patch(
        f'/api/v1/skills/{skill_id}',
        json={
            'expected_version': skill.json()['version'],
            'description': 'Updated integration-test skill.',
        },
    )
    _assert_success(updated_skill)

    persona = api_client.post(
        '/api/v1/personas',
        json=_persona_payload(skill_id),
    )
    _assert_created(persona)
    persona_id = persona.json()['id']
    _assert_success(api_client.get(f'/api/v1/personas/{persona_id}'))
    _assert_success(api_client.get('/api/v1/personas'))
    updated_persona = api_client.patch(
        f'/api/v1/personas/{persona_id}',
        json={
            'expected_version': persona.json()['version'],
            'description': 'Updated integration-test persona.',
        },
    )
    _assert_success(updated_persona)

    activity = api_client.post(
        '/api/v1/activities',
        json={
            'name': 'Standalone approval',
            'description': 'Approve an integration release.',
            'type': 'approval',
            'config': {},
        },
    )
    _assert_created(activity)
    activity_id = activity.json()['id']
    _assert_success(api_client.get(f'/api/v1/activities/{activity_id}'))
    _assert_success(api_client.get('/api/v1/activities?offset=0'))
    _assert_success(
        api_client.patch(
            f'/api/v1/activities/{activity_id}',
            json={'description': 'Updated integration approval.'},
        )
    )
    _assert_success(
        api_client.get(f'/api/v1/activities/{activity_id}/changelog?offset=0')
    )

    worker = api_client.post(
        '/api/v1/workers',
        json={
            'project_id': project_id,
            'harnesses': [{'kind': 'louie', 'version': 'v1', 'config': {}}],
        },
    )
    _assert_created(worker)
    worker_id = worker.json()['id']
    _assert_success(api_client.get('/api/v1/workers'))
    _assert_success(api_client.get(f'/api/v1/workers/{worker_id}'))
    _assert_success(
        api_client.post(
            f'/api/v1/workers/{worker_id}/heartbeat',
            json={'harnesses': [{'kind': 'louie', 'version': 'v1', 'config': {}}]},
        )
    )
    _assert_success(
        api_client.get(f'/api/v1/projects/{project_id}/workers')
    )

    pipeline = api_client.post(
        '/api/v1/pipelines',
        headers=project_headers,
        json=_pipeline_payload(model_id, persona_id),
    )
    _assert_created(pipeline)
    pipeline_id = pipeline.json()['id']
    _assert_success(
        api_client.get(
            f'/api/v1/pipelines/{pipeline_id}',
            headers=project_headers,
        )
    )
    _assert_success(
        api_client.get(
            '/api/v1/pipelines?offset=0&status=active&search=Integration',
            headers=project_headers,
        )
    )
    _assert_success(
        api_client.patch(
            f'/api/v1/pipelines/{pipeline_id}',
            headers=project_headers,
            json={'description': 'Updated integration pipeline.'},
        )
    )
    _assert_success(
        api_client.get(
            f'/api/v1/pipelines/{pipeline_id}/changelog?offset=0',
            headers=project_headers,
        )
    )

    run = api_client.post(
        f'/api/v1/pipelines/{pipeline_id}/runs',
        headers=project_headers,
        json={'input': 'Produce an integration-test answer.'},
    )
    _assert_created(run)
    run_id = run.json()['id']
    _assert_success(
        api_client.get('/api/v1/pipeline-runs?offset=0', headers=project_headers)
    )
    _assert_success(
        api_client.get(
            f'/api/v1/pipelines/{pipeline_id}/runs/{run_id}',
            headers=project_headers,
        )
    )
    _assert_success(
        api_client.post(
            f'/api/v1/pipelines/{pipeline_id}/runs/{run_id}/start',
            headers=project_headers,
            json={},
        )
    )
    readiness = api_client.get(
        f'/api/v1/pipelines/{pipeline_id}/runs/{run_id}/readiness',
        headers=project_headers,
    )
    _assert_success(readiness)
    assert readiness.json()['status'] == 'ready'
    claimable = api_client.get(
        f'/api/v1/pipelines/{pipeline_id}/runs?claimable=true&worker_id={worker_id}',
        headers=project_headers,
    )
    _assert_success(claimable)
    etag = claimable.json()['items'][0]['etag']
    claim = api_client.patch(
        f'/api/v1/pipelines/{pipeline_id}/runs/{run_id}',
        headers={**project_headers, 'If-Match': etag},
        json={'worker_id': worker_id, 'status': 'claimed'},
    )
    _assert_success(claim)
    lease_token = claim.json()['lease_token']
    assert lease_token
    _assert_success(
        api_client.post(
            f'/api/v1/pipelines/{pipeline_id}/runs/{run_id}/lease',
            headers=project_headers,
            json={'lease_token': lease_token},
        )
    )
    events = api_client.get(
        f'/api/v1/pipelines/{pipeline_id}/runs/{run_id}/events',
        headers=project_headers,
    )
    _assert_success(events)
    assert events.json()['total'] >= 2


def _create_project(
    client: TestClient,
    name: str,
) -> dict[str, object]:
    """Create one Project and return its public representation."""

    response = client.post('/api/v1/projects', json={'name': name})
    _assert_created(response)
    return response.json()


def _skill_payload() -> dict[str, object]:
    """Build a valid custom Skill payload for lifecycle coverage."""

    return {
        'name': 'Integration skill',
        'description': 'Validates the composed API lifecycle.',
        'instructions': 'Review the response for correctness.',
        'metadata': {'applies_when': ['integration']},
    }


def _persona_payload(skill_id: str) -> dict[str, object]:
    """Build a valid Persona referencing the custom Skill."""

    return {
        'name': 'integration_persona',
        'description': 'Supports the composed API lifecycle.',
        'instructions': 'Produce a concise implementation.',
        'skill_ids': [skill_id],
    }


def _pipeline_payload(
    model_id: str,
    persona_id: str,
) -> dict[str, object]:
    """Build a runnable direct-loop Pipeline definition."""

    return {
        'name': 'Integration pipeline',
        'description': 'Exercises the worker claim lifecycle.',
        'steps': [
            {
                'name': 'Generate implementation',
                'description': 'Generate a deterministic test artifact.',
                'type': 'direct_loop',
                'model_id': model_id,
                'config': {
                    'stop_conditions': {'max_iterations': 1},
                    'agents': [
                        {
                            'model_id': model_id,
                            'persona_id': persona_id,
                            'role': 'generator',
                        }
                    ],
                    'output_contract': {
                        'type': 'text',
                        'description': 'A test artifact.',
                    },
                },
            }
        ],
    }


def _assert_success(response: Response) -> None:
    """Assert a response is successful while retaining its failure body."""

    assert 200 <= response.status_code < 300, response.text


def _assert_created(response: Response) -> None:
    """Assert a resource-creation response uses the REST creation status."""

    assert response.status_code == 201, response.text
