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

        token = request.cookies.get(SESSION_COOKIE_NAME)
        if token:
            service = getattr(
                request.app.state,
                'account_authentication_service',
                None,
            )
            if not isinstance(service, AccountAuthenticationService):
                raise RuntimeError('Account authentication is not configured.')
            user = await service.current_user(token=token)
            if user is not None:
                request.state.user_id = user.id
        return await call_next(request)
