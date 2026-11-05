"""Public local-account setup and session routes."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from src.controllers.authentication import AuthenticationController
from src.middleware.session_auth import SESSION_COOKIE_NAME
from src.schemas.authentication import (
    AccountCredentialsRequest,
    SessionStatusResponse,
    SetupStatusResponse,
)

from .dependencies import (
    RequestContext,
    get_authentication_controller,
    get_request_context,
)


router = APIRouter(prefix='/auth', tags=['Authentication'])
ControllerDependency = Annotated[
    AuthenticationController,
    Depends(get_authentication_controller),
]
SessionCookie = Annotated[
    str | None,
    Cookie(alias=SESSION_COOKIE_NAME),
]
_SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


@router.get('/setup-status', response_model=SetupStatusResponse)
async def get_setup_status(
    controller: ControllerDependency,
) -> SetupStatusResponse:
    """Return whether the instance accepts initial administrator setup."""

    return await controller.setup_status()


@router.get('/session', response_model=SessionStatusResponse)
async def get_session_status(
    request: Request,
    controller: ControllerDependency,
) -> SessionStatusResponse:
    """Return setup status and the authenticated browser account."""

    user_id = getattr(request.state, 'user_id', None)
    return await controller.status(
        user_id=user_id if isinstance(user_id, str) else None,
    )


@router.post('/setup', response_model=SessionStatusResponse)
async def setup_administrator(
    payload: AccountCredentialsRequest,
    response: Response,
    controller: ControllerDependency,
) -> SessionStatusResponse:
    """Complete one-time initial administrator setup."""

    result, token = await controller.setup(
        username=payload.username,
        password=payload.password,
    )
    _set_session_cookie(response, token)
    return result


@router.post('/login', response_model=SessionStatusResponse)
async def login(
    payload: AccountCredentialsRequest,
    response: Response,
    controller: ControllerDependency,
) -> SessionStatusResponse:
    """Authenticate one local account and issue a browser session."""

    result, token = await controller.login(
        username=payload.username,
        password=payload.password,
    )
    _set_session_cookie(response, token)
    return result


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    controller: ControllerDependency,
    context: Annotated[RequestContext, Depends(get_request_context)],
    session_token: SessionCookie = None,
) -> None:
    """Revoke the browser session and clear its cookie."""

    del context
    await controller.logout(token=session_token)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path='/',
        secure=True,
        httponly=True,
        samesite='lax',
    )


def _set_session_cookie(response: Response, token: str) -> None:
    """Store the opaque session only in a browser-protected cookie."""

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=_SESSION_MAX_AGE_SECONDS,
        path='/',
        secure=True,
        httponly=True,
        samesite='lax',
    )
