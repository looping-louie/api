"""Development-only authentication middleware."""

from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


RequestHandler = Callable[[Request], Awaitable[Response]]


class DevelopmentAuthMiddleware(BaseHTTPMiddleware):
    """Inject a fixed local user when real authentication is disabled."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        user_id: str,
    ) -> None:
        super().__init__(app)

        normalized_user_id = user_id.strip()

        if not normalized_user_id:
            raise ValueError(
                "Development authentication requires a user ID."
            )

        self._user_id = normalized_user_id

    async def dispatch(
        self,
        request: Request,
        call_next: RequestHandler,
    ) -> Response:
        """Attach the local user to the request."""

        if not getattr(request.state, "user_id", None):
            request.state.user_id = self._user_id

        return await call_next(request)
