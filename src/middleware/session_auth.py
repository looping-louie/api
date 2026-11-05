"""Cookie-backed authentication middleware for browser requests."""

from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.services.authentication import AccountAuthenticationService


SESSION_COOKIE_NAME = 'looping_louie_session'
RequestHandler = Callable[[Request], Awaitable[Response]]


class SessionAuthenticationMiddleware(BaseHTTPMiddleware):
    """Resolve an active local account from the opaque session cookie."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestHandler,
    ) -> Response:
        """Attach the verified session user to the request when present."""

        service = getattr(
            request.app.state,
            'account_authentication_service',
            None,
        )
        if not isinstance(service, AccountAuthenticationService):
            raise RuntimeError('Account authentication is not configured.')
        token = request.cookies.get(SESSION_COOKIE_NAME)
        if token:
            user = await service.current_user(token=token)
            if user is not None:
                request.state.user_id = user.id
        if not getattr(request.state, 'user_id', None):
            bearer_token = _bearer_token(request)
            if bearer_token is not None:
                user = await service.current_user_from_personal_access_token(
                    token=bearer_token,
                )
                if user is not None:
                    request.state.user_id = user.id
                else:
                    service_account = await service.current_service_account(
                        token=bearer_token,
                    )
                    if service_account is not None:
                        request.state.service_account = service_account
        return await call_next(request)


def _bearer_token(request: Request) -> str | None:
    """Return one validly formatted bearer token from an API request."""

    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    if scheme.casefold() != 'bearer' or not token.strip():
        return None
    return token.strip()
