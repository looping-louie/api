"""Persistence contract for server-side user sessions."""

from typing import Protocol

from src.models.user_session import UserSession


class UserSessionRepository(Protocol):
    """Persist opaque browser session digests."""

    async def create(self, session: UserSession) -> UserSession:
        """Store one session."""
        raise NotImplementedError

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> UserSession | None:
        """Return one session selected by its digest."""
        raise NotImplementedError

    async def delete_by_token_hash(self, *, token_hash: str) -> None:
        """Revoke one session selected by its digest."""
        raise NotImplementedError

    async def delete_by_user_id(self, *, user_id: str) -> None:
        """Revoke every browser session belonging to one user."""
        raise NotImplementedError
