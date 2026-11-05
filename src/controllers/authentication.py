"""HTTP-oriented local account authentication controller."""

from src.models.user import UserDocument
from src.schemas.authentication import (
    SessionStatusResponse,
    SessionUserResponse,
    SetupStatusResponse,
)
from src.services.authentication import AccountAuthenticationService


class AuthenticationController:
    """Translate local-account authentication results into HTTP responses."""

    def __init__(self, *, service: AccountAuthenticationService) -> None:
        """Store the account authentication application service."""

        self._service = service

    async def setup_status(self) -> SetupStatusResponse:
        """Return whether the initial administrator can still be created."""

        return SetupStatusResponse(
            setup_required=await self._service.bootstrap_available(),
        )

    async def status(self, *, user_id: str | None) -> SessionStatusResponse:
        """Describe setup state and the optional authenticated account."""

        user = (
            await self._service.current_user_id(user_id=user_id)
            if user_id is not None
            else None
        )
        return SessionStatusResponse(
            setup_required=await self._service.bootstrap_available(),
            user=_session_user_response(user) if user is not None else None,
        )

    async def setup(
        self,
        *,
        username: str,
        password: str,
    ) -> tuple[SessionStatusResponse, str]:
        """Create the initial administrator and return its session token."""

        user, token = await self._service.bootstrap_administrator(
            username=username,
            password=password,
        )
        return SessionStatusResponse(
            setup_required=False,
            user=_session_user_response(user),
        ), token

    async def login(
        self,
        *,
        username: str,
        password: str,
    ) -> tuple[SessionStatusResponse, str]:
        """Authenticate one local account and return its session token."""

        user, token = await self._service.authenticate(
            username=username,
            password=password,
        )
        return SessionStatusResponse(
            setup_required=False,
            user=_session_user_response(user),
        ), token

    async def logout(self, *, token: str | None) -> None:
        """Revoke an optional session token without exposing its validity."""

        if token is not None:
            await self._service.logout(token=token)


def _session_user_response(document: UserDocument) -> SessionUserResponse:
    """Map one credentialed User document to browser-safe session identity."""

    if document.username is None:
        raise RuntimeError('Authenticated account is missing a username.')
    return SessionUserResponse(
        id=document.id,
        username=document.username,
        role=document.role,
    )
