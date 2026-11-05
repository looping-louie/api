"""Local-account bootstrap, credential verification, and session issuance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from src.models.user import UserDocument
from src.models.user_session import UserSession
from src.repositories.user_sessions import UserSessionRepository
from src.repositories.users import UserRepository

from .passwords import PasswordHasher


LOCAL_USER_ID = 'local-user'
SESSION_DURATION = timedelta(days=30)


class AuthenticationError(Exception):
    """Raised when supplied local-account credentials are invalid."""


class BootstrapUnavailableError(Exception):
    """Raised when an initial administrator account already exists."""


class AccountAccessDeniedError(Exception):
    """Raised when a non-administrator manages local accounts."""


class AccountNotFoundError(Exception):
    """Raised when a requested local account does not exist."""


class AccountSelfModificationError(Exception):
    """Raised when an administrator modifies their own access."""


class AccountUsernameConflictError(Exception):
    """Raised when a local username already belongs to an account."""


class AccountAuthenticationService:
    """Coordinate initial local-account setup and server-side browser sessions."""

    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: UserSessionRepository,
        password_hasher: PasswordHasher,
        id_factory: Callable[[], str],
        token_factory: Callable[[], str] = lambda: token_urlsafe(32),
        clock: Callable[[], datetime],
    ) -> None:
        """Store account persistence and generation dependencies."""

        self._users = users
        self._sessions = sessions
        self._password_hasher = password_hasher
        self._id_factory = id_factory
        self._token_factory = token_factory
        self._clock = clock

    async def bootstrap_available(self) -> bool:
        """Return whether the instance accepts its first administrator setup."""

        return not await self._users.has_local_accounts()

    async def bootstrap_administrator(
        self,
        *,
        username: str,
        password: str,
    ) -> tuple[UserDocument, str]:
        """Upgrade the legacy local user into the first administrator."""

        if not await self.bootstrap_available():
            raise BootstrapUnavailableError
        current = await self._users.get(user_id=LOCAL_USER_ID)
        if current is None:
            raise RuntimeError('The local bootstrap user is missing.')
        now = self._clock()
        user = await self._users.update(replace(
            current,
            username=_require_username(username),
            password_hash=self._password_hasher.hash(_require_password(password)),
            role='admin',
            is_active=True,
            updated_at=now,
        ))
        return user, await self._create_session(user_id=user.id, now=now)

    async def authenticate(
        self,
        *,
        username: str,
        password: str,
    ) -> tuple[UserDocument, str]:
        """Verify active account credentials and issue a new opaque session."""

        user = await self._users.get_by_username(username=username.strip())
        if (
            user is None
            or not user.is_active
            or user.password_hash is None
            or not self._password_hasher.verify(
                password=password,
                encoded_hash=user.password_hash,
            )
        ):
            raise AuthenticationError
        return user, await self._create_session(
            user_id=user.id,
            now=self._clock(),
        )

    async def current_user(self, *, token: str) -> UserDocument | None:
        """Return the active user authenticated by an unexpired session token."""

        session = await self._sessions.get_by_token_hash(
            token_hash=_token_hash(token),
        )
        if session is None:
            return None
        if session.expires_at <= self._clock():
            await self._sessions.delete_by_token_hash(
                token_hash=session.token_hash,
            )
            return None
        user = await self._users.get(user_id=session.user_id)
        if user is None or not user.is_active:
            await self._sessions.delete_by_token_hash(
                token_hash=session.token_hash,
            )
            return None
        return user

    async def current_user_id(self, *, user_id: str) -> UserDocument | None:
        """Return the active local account for a middleware-authenticated ID."""

        user = await self._users.get(user_id=user_id)
        if user is None or not user.is_active or user.username is None:
            return None
        return user

    async def logout(self, *, token: str) -> None:
        """Revoke the session represented by one raw browser token."""

        await self._sessions.delete_by_token_hash(
            token_hash=_token_hash(token),
        )

    async def list_accounts(self, *, administrator_id: str) -> list[UserDocument]:
        """Return the instance local accounts to an authenticated administrator."""

        await self._require_administrator(user_id=administrator_id)
        return await self._users.list_local_accounts()

    async def create_member(
        self,
        *,
        administrator_id: str,
        username: str,
        password: str,
    ) -> UserDocument:
        """Create an active local member account."""

        await self._require_administrator(user_id=administrator_id)
        normalized_username = _require_username(username)
        if await self._users.get_by_username(username=normalized_username):
            raise AccountUsernameConflictError
        now = self._clock()
        return await self._users.create_if_absent(UserDocument(
            id=self._id_factory(),
            created_at=now,
            updated_at=now,
            username=normalized_username,
            password_hash=self._password_hasher.hash(
                _require_password(password),
            ),
        ))

    async def reset_member_password(
        self,
        *,
        administrator_id: str,
        user_id: str,
        password: str,
    ) -> UserDocument:
        """Replace one member password and revoke every existing session."""

        await self._require_modifiable_member(
            administrator_id=administrator_id,
            user_id=user_id,
        )
        user = await self._require_account(user_id=user_id)
        updated = await self._users.update(replace(
            user,
            password_hash=self._password_hasher.hash(
                _require_password(password),
            ),
            updated_at=self._clock(),
        ))
        await self._sessions.delete_by_user_id(user_id=user_id)
        return updated

    async def set_member_active(
        self,
        *,
        administrator_id: str,
        user_id: str,
        is_active: bool,
    ) -> UserDocument:
        """Activate or deactivate one member and revoke existing sessions."""

        await self._require_modifiable_member(
            administrator_id=administrator_id,
            user_id=user_id,
        )
        user = await self._require_account(user_id=user_id)
        updated = await self._users.update(replace(
            user,
            is_active=is_active,
            updated_at=self._clock(),
        ))
        await self._sessions.delete_by_user_id(user_id=user_id)
        return updated

    async def _create_session(self, *, user_id: str, now: datetime) -> str:
        """Persist only a digest while returning the raw token to the caller."""

        token = self._token_factory()
        await self._sessions.create(UserSession(
            id=self._id_factory(),
            user_id=user_id,
            token_hash=_token_hash(token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + SESSION_DURATION,
        ))
        return token

    async def _require_administrator(self, *, user_id: str) -> UserDocument:
        """Return an active administrator allowed to manage accounts."""

        user = await self._users.get(user_id=user_id)
        if user is None or not user.is_active or user.role != 'admin':
            raise AccountAccessDeniedError
        return user

    async def _require_modifiable_member(
        self,
        *,
        administrator_id: str,
        user_id: str,
    ) -> None:
        """Reject self-management and management of other administrators."""

        await self._require_administrator(user_id=administrator_id)
        if user_id == administrator_id:
            raise AccountSelfModificationError
        account = await self._require_account(user_id=user_id)
        if account.role == 'admin':
            raise AccountSelfModificationError

    async def _require_account(self, *, user_id: str) -> UserDocument:
        """Return an existing credentialed local account."""

        user = await self._users.get(user_id=user_id)
        if user is None or user.username is None:
            raise AccountNotFoundError
        return user


def _require_username(value: str) -> str:
    """Normalize one required local-account username."""

    normalized = value.strip()
    if not normalized:
        raise ValueError('username must not be empty.')
    return normalized


def _require_password(value: str) -> str:
    """Require a password long enough to resist trivial guessing."""

    if len(value) < 12:
        raise ValueError('password must contain at least 12 characters.')
    return value


def _token_hash(token: str) -> str:
    """Return a stable digest for server-side opaque-session lookup."""

    return sha256(token.encode('utf-8')).hexdigest()
