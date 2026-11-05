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


def test_administrator_manages_member_accounts(
    session_api_client: TestClient,
) -> None:
    """Only administrators can provision, reset, and deactivate members."""

    setup = session_api_client.post(
        '/api/v1/auth/setup',
        json={'username': 'administrator', 'password': 'correct horse battery'},
    )
    assert setup.status_code == 200
    administrator_token = session_api_client.cookies.get('looping_louie_session')
    assert administrator_token is not None

    created = session_api_client.post(
        '/api/v1/auth/accounts',
        json={'username': 'member', 'password': 'member password'},
    )
    accounts = session_api_client.get('/api/v1/auth/accounts')

    assert created.status_code == 201
    member = created.json()
    assert member['username'] == 'member'
    assert member['role'] == 'member'
    assert member['is_active'] is True
    assert [account['username'] for account in accounts.json()] == [
        'administrator',
        'member',
    ]

    member_login = session_api_client.post(
        '/api/v1/auth/login',
        json={'username': 'member', 'password': 'member password'},
    )
    assert member_login.status_code == 200
    member_token = session_api_client.cookies.get('looping_louie_session')
    assert member_token is not None

    unauthorized = session_api_client.post(
        '/api/v1/auth/accounts',
        json={'username': 'another', 'password': 'another password'},
    )
    assert unauthorized.status_code == 403

    _set_session_cookie(session_api_client, administrator_token)
    reset = session_api_client.patch(
        f'/api/v1/auth/accounts/{member["id"]}/password',
        json={'password': 'replaced member password'},
    )
    assert reset.status_code == 200

    _set_session_cookie(session_api_client, member_token)
    revoked_session = session_api_client.get('/api/v1/users/me')
    assert revoked_session.status_code == 401

    member_relogin = session_api_client.post(
        '/api/v1/auth/login',
        json={'username': 'member', 'password': 'replaced member password'},
    )
    assert member_relogin.status_code == 200

    _set_session_cookie(session_api_client, administrator_token)
    deactivated = session_api_client.patch(
        f'/api/v1/auth/accounts/{member["id"]}/activation',
        json={'is_active': False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()['is_active'] is False

    disabled_login = session_api_client.post(
        '/api/v1/auth/login',
        json={'username': 'member', 'password': 'replaced member password'},
    )
    assert disabled_login.status_code == 401


def test_user_manages_and_uses_personal_access_tokens(
    session_api_client: TestClient,
) -> None:
    """A user receives each opaque token once and can revoke it."""

    setup = session_api_client.post(
        '/api/v1/auth/setup',
        json={'username': 'administrator', 'password': 'correct horse battery'},
    )
    assert setup.status_code == 200

    created = session_api_client.post(
        '/api/v1/auth/personal-access-tokens',
        json={'name': 'Postman'},
    )

    assert created.status_code == 201
    token = created.json()
    assert token['name'] == 'Postman'
    assert token['token']
    assert token['expires_at'] is not None

    bearer_client = TestClient(
        session_api_client.app,
        base_url='https://testserver',
    )
    projects = bearer_client.get(
        '/api/v1/projects',
        headers={'Authorization': f'Bearer {token["token"]}'},
    )
    assert projects.status_code == 200
    assert projects.json()[0]['id'] == 'local-project'

    listed = session_api_client.get('/api/v1/auth/personal-access-tokens')
    assert listed.status_code == 200
    assert listed.json()[0]['id'] == token['id']
    assert 'token' not in listed.json()[0]

    revoked = session_api_client.delete(
        f'/api/v1/auth/personal-access-tokens/{token["id"]}',
    )
    assert revoked.status_code == 204

    denied = bearer_client.get(
        '/api/v1/projects',
        headers={'Authorization': f'Bearer {token["token"]}'},
    )
    assert denied.status_code == 401


def test_administrator_manages_project_scoped_service_accounts(
    session_api_client: TestClient,
) -> None:
    """Service account secrets are shown once and revocable by administrators."""

    setup = session_api_client.post(
        '/api/v1/auth/setup',
        json={'username': 'administrator', 'password': 'correct horse battery'},
    )
    assert setup.status_code == 200

    created = session_api_client.post(
        '/api/v1/auth/service-accounts',
        json={'name': 'Production runtime', 'project_ids': ['local-project']},
    )

    assert created.status_code == 201
    account = created.json()
    assert account['name'] == 'Production runtime'
    assert account['project_ids'] == ['local-project']
    assert account['token']
    assert account['expires_at'] is not None

    listed = session_api_client.get('/api/v1/auth/service-accounts')
    assert listed.status_code == 200
    assert listed.json()[0]['id'] == account['id']
    assert 'token' not in listed.json()[0]

    revoked = session_api_client.delete(
        f'/api/v1/auth/service-accounts/{account["id"]}',
    )
    assert revoked.status_code == 204


def _set_session_cookie(client: TestClient, token: str) -> None:
    """Replace the test browser session cookie with one saved opaque token."""

    client.cookies.clear()
    client.cookies.set(
        'looping_louie_session',
        token,
    )
