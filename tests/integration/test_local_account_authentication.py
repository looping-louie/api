"""Integration coverage for browser local-account authentication."""

from fastapi.testclient import TestClient


def test_setup_upgrades_local_user_and_preserves_project_access(
    session_api_client: TestClient,
) -> None:
    """The first administrator inherits all resources owned by local-user."""

    before_setup = session_api_client.get('/api/v1/auth/setup-status')

    assert before_setup.status_code == 200
    assert before_setup.json() == {'setup_required': True}

    setup = session_api_client.post(
        '/api/v1/auth/setup',
        json={'username': 'administrator', 'password': 'correct horse battery'},
    )

    assert setup.status_code == 200
    assert setup.json() == {
        'setup_required': False,
        'user': {
            'id': 'local-user',
            'username': 'administrator',
            'role': 'admin',
        },
    }
    assert setup.headers['set-cookie'].startswith('looping_louie_session=')

    projects = session_api_client.get('/api/v1/projects')

    assert projects.status_code == 200
    assert [project['id'] for project in projects.json()] == ['local-project']


def test_header_cannot_impersonate_a_user(
    session_api_client: TestClient,
) -> None:
    """A browser-supplied identity header never authenticates the request."""

    response = session_api_client.get(
        '/api/v1/users/me',
        headers={'X-User-ID': 'local-user'},
    )

    assert response.status_code == 401
    assert response.json()['detail']['code'] == 'authentication_required'


def test_login_failures_are_generic_and_successful_login_uses_cookie(
    session_api_client: TestClient,
) -> None:
    """Credential failures disclose no account existence information."""

    setup = session_api_client.post(
        '/api/v1/auth/setup',
        json={'username': 'administrator', 'password': 'correct horse battery'},
    )
    assert setup.status_code == 200

    session_api_client.post('/api/v1/auth/logout')
    incorrect_password = session_api_client.post(
        '/api/v1/auth/login',
        json={'username': 'administrator', 'password': 'incorrect password'},
    )
    unknown_username = session_api_client.post(
        '/api/v1/auth/login',
        json={'username': 'unknown', 'password': 'incorrect password'},
    )

    assert incorrect_password.status_code == 401
    assert unknown_username.status_code == 401
    assert incorrect_password.json() == unknown_username.json()

    login = session_api_client.post(
        '/api/v1/auth/login',
        json={'username': 'administrator', 'password': 'correct horse battery'},
    )
    current_user = session_api_client.get('/api/v1/users/me')

    assert login.status_code == 200
    assert current_user.status_code == 200
    assert current_user.json()['id'] == 'local-user'


def test_logout_revokes_the_server_side_session(
    session_api_client: TestClient,
) -> None:
    """A cleared browser cookie cannot be replayed after logout."""

    setup = session_api_client.post(
        '/api/v1/auth/setup',
        json={'username': 'administrator', 'password': 'correct horse battery'},
    )
    assert setup.status_code == 200
    token = session_api_client.cookies.get('looping_louie_session')
    assert token is not None

    logout = session_api_client.post('/api/v1/auth/logout')
    session_api_client.cookies.set(
        'looping_louie_session',
        token,
        domain='testserver',
        path='/',
    )
    replay = session_api_client.get('/api/v1/users/me')

    assert logout.status_code == 204
    assert replay.status_code == 401
