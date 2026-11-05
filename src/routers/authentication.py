"""Public local-account setup and session routes."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Path, Request, Response, status

from src.controllers.authentication import AuthenticationController
from src.middleware.session_auth import SESSION_COOKIE_NAME
from src.schemas.authentication import (
    AccountCredentialsRequest,
    LocalAccountResponse,
    MemberAccountActivationRequest,
    MemberAccountCreateRequest,
    MemberAccountPasswordResetRequest,
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
AccountIdPath = Annotated[str, Path(min_length=1)]


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
    request: Request,
    response: Response,
    controller: ControllerDependency,
) -> SessionStatusResponse:
    """Complete one-time initial administrator setup."""

    result, token = await controller.setup(
        username=payload.username,
        password=payload.password,
    )
    _set_session_cookie(
        response,
        token,
        secure=_session_cookie_secure(request),
    )
    return result


@router.post('/login', response_model=SessionStatusResponse)
async def login(
    payload: AccountCredentialsRequest,
    request: Request,
    response: Response,
    controller: ControllerDependency,
) -> SessionStatusResponse:
    """Authenticate one local account and issue a browser session."""

    result, token = await controller.login(
        username=payload.username,
        password=payload.password,
    )
    _set_session_cookie(
        response,
        token,
        secure=_session_cookie_secure(request),
    )
    return result


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
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
        secure=_session_cookie_secure(request),
        httponly=True,
        samesite='lax',
    )


@router.get('/accounts', response_model=list[LocalAccountResponse])
async def list_accounts(
    context: Annotated[RequestContext, Depends(get_request_context)],
    controller: ControllerDependency,
) -> list[LocalAccountResponse]:
    """List local accounts for an authenticated administrator."""

    return await controller.list_accounts(administrator_id=context.user_id)


@router.post(
    '/accounts',
    response_model=LocalAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_member_account(
    payload: MemberAccountCreateRequest,
    context: Annotated[RequestContext, Depends(get_request_context)],
    controller: ControllerDependency,
) -> LocalAccountResponse:
    """Create one local member account as an authenticated administrator."""

    return await controller.create_member(
        administrator_id=context.user_id,
        payload=payload,
    )


@router.patch('/accounts/{user_id}/password', response_model=LocalAccountResponse)
async def reset_member_account_password(
    user_id: AccountIdPath,
    payload: MemberAccountPasswordResetRequest,
    context: Annotated[RequestContext, Depends(get_request_context)],
    controller: ControllerDependency,
) -> LocalAccountResponse:
    """Replace one local member password as an authenticated administrator."""

    return await controller.reset_member_password(
        administrator_id=context.user_id,
        user_id=user_id,
        payload=payload,
    )


@router.patch('/accounts/{user_id}/activation', response_model=LocalAccountResponse)
async def set_member_account_active(
    user_id: AccountIdPath,
    payload: MemberAccountActivationRequest,
    context: Annotated[RequestContext, Depends(get_request_context)],
    controller: ControllerDependency,
) -> LocalAccountResponse:
    """Activate or deactivate one local member as an administrator."""

    return await controller.set_member_active(
        administrator_id=context.user_id,
        user_id=user_id,
        payload=payload,
    )


def _set_session_cookie(
    response: Response,
    token: str,
    *,
    secure: bool,
) -> None:
    """Store the opaque session only in a browser-protected cookie."""

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=_SESSION_MAX_AGE_SECONDS,
        path='/',
        secure=secure,
        httponly=True,
        samesite='lax',
    )


def _session_cookie_secure(request: Request) -> bool:
    """Return the application-configured browser-cookie transport policy."""

    secure = getattr(request.app.state, 'session_cookie_secure', None)
    if not isinstance(secure, bool):
        raise RuntimeError('Session cookie security has not been configured.')
    return secure
