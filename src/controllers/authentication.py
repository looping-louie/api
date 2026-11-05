"""HTTP-oriented local account authentication controller."""

from src.models.user import UserDocument
from src.models.personal_access_token import PersonalAccessToken
from src.models.service_account import ServiceAccount
from src.schemas.authentication import (
    LocalAccountResponse,
    MemberAccountActivationRequest,
    MemberAccountCreateRequest,
    MemberAccountPasswordResetRequest,
    PersonalAccessTokenCreateRequest,
    PersonalAccessTokenCreatedResponse,
    PersonalAccessTokenResponse,
    ServiceAccountCreateRequest,
    ServiceAccountCreatedResponse,
    ServiceAccountResponse,
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

    async def list_accounts(
        self,
        *,
        administrator_id: str,
    ) -> list[LocalAccountResponse]:
        """Return accounts visible to one authenticated administrator."""

        return [
            _local_account_response(account)
            for account in await self._service.list_accounts(
                administrator_id=administrator_id,
            )
        ]

    async def create_member(
        self,
        *,
        administrator_id: str,
        payload: MemberAccountCreateRequest,
    ) -> LocalAccountResponse:
        """Create a local member account for one administrator."""

        return _local_account_response(
            await self._service.create_member(
                administrator_id=administrator_id,
                username=payload.username,
                password=payload.password,
            ),
        )

    async def reset_member_password(
        self,
        *,
        administrator_id: str,
        user_id: str,
        payload: MemberAccountPasswordResetRequest,
    ) -> LocalAccountResponse:
        """Replace one local member password."""

        return _local_account_response(
            await self._service.reset_member_password(
                administrator_id=administrator_id,
                user_id=user_id,
                password=payload.password,
            ),
        )

    async def set_member_active(
        self,
        *,
        administrator_id: str,
        user_id: str,
        payload: MemberAccountActivationRequest,
    ) -> LocalAccountResponse:
        """Activate or deactivate one local member account."""

        return _local_account_response(
            await self._service.set_member_active(
                administrator_id=administrator_id,
                user_id=user_id,
                is_active=payload.is_active,
            ),
        )

    async def list_personal_access_tokens(
        self,
        *,
        user_id: str,
    ) -> list[PersonalAccessTokenResponse]:
        """Return the authenticated user's personal access tokens."""

        return [
            _personal_access_token_response(token)
            for token in await self._service.list_personal_access_tokens(
                user_id=user_id,
            )
        ]

    async def create_personal_access_token(
        self,
        *,
        user_id: str,
        payload: PersonalAccessTokenCreateRequest,
    ) -> PersonalAccessTokenCreatedResponse:
        """Issue one named personal access token to its authenticated owner."""

        token, raw_token = await self._service.create_personal_access_token(
            user_id=user_id,
            name=payload.name,
            expires_at=payload.expires_at,
            use_default_expiry='expires_at' not in payload.model_fields_set,
        )
        return PersonalAccessTokenCreatedResponse(
            **_personal_access_token_response(token).model_dump(),
            token=raw_token,
        )

    async def revoke_personal_access_token(
        self,
        *,
        user_id: str,
        token_id: str,
    ) -> None:
        """Revoke one personal access token belonging to its owner."""

        await self._service.revoke_personal_access_token(
            user_id=user_id,
            token_id=token_id,
        )

    async def list_service_accounts(
        self,
        *,
        administrator_id: str,
    ) -> list[ServiceAccountResponse]:
        """Return runtime service accounts managed by an administrator."""

        return [
            _service_account_response(account)
            for account in await self._service.list_service_accounts(
                administrator_id=administrator_id,
            )
        ]

    async def create_service_account(
        self,
        *,
        administrator_id: str,
        payload: ServiceAccountCreateRequest,
    ) -> ServiceAccountCreatedResponse:
        """Issue one project-scoped runtime credential."""

        account, raw_token = await self._service.create_service_account(
            administrator_id=administrator_id,
            name=payload.name,
            project_ids=tuple(payload.project_ids),
            expires_at=payload.expires_at,
            use_default_expiry='expires_at' not in payload.model_fields_set,
        )
        return ServiceAccountCreatedResponse(
            **_service_account_response(account).model_dump(),
            token=raw_token,
        )

    async def revoke_service_account(
        self,
        *,
        administrator_id: str,
        account_id: str,
    ) -> None:
        """Revoke one runtime credential administered by the caller."""

        await self._service.revoke_service_account(
            administrator_id=administrator_id,
            account_id=account_id,
        )


def _session_user_response(document: UserDocument) -> SessionUserResponse:
    """Map one credentialed User document to browser-safe session identity."""

    if document.username is None:
        raise RuntimeError('Authenticated account is missing a username.')
    return SessionUserResponse(
        id=document.id,
        username=document.username,
        role=document.role,
    )


def _local_account_response(document: UserDocument) -> LocalAccountResponse:
    """Map one credentialed User document to administrator-visible metadata."""

    return LocalAccountResponse(
        **_session_user_response(document).model_dump(),
        is_active=document.is_active,
    )


def _personal_access_token_response(
    token: PersonalAccessToken,
) -> PersonalAccessTokenResponse:
    """Map one token to credential-safe API metadata."""

    return PersonalAccessTokenResponse(
        id=token.id,
        name=token.name,
        created_at=token.created_at,
        last_used_at=token.last_used_at,
        expires_at=token.expires_at,
        revoked_at=token.revoked_at,
    )


def _service_account_response(
    account: ServiceAccount,
) -> ServiceAccountResponse:
    """Map one service account to credential-safe API metadata."""

    return ServiceAccountResponse(
        id=account.id,
        name=account.name,
        project_ids=list(account.project_ids),
        created_at=account.created_at,
        last_used_at=account.last_used_at,
        expires_at=account.expires_at,
        revoked_at=account.revoked_at,
    )
