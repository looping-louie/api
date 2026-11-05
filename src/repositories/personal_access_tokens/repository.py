"""Persistence contract for personal access tokens."""

from datetime import datetime
from typing import Protocol

from src.models.personal_access_token import PersonalAccessToken


class PersonalAccessTokenRepository(Protocol):
    """Persist opaque personal access-token digests."""

    async def create(self, token: PersonalAccessToken) -> PersonalAccessToken:
        """Store one token."""
        raise NotImplementedError

    async def list_for_user(self, *, user_id: str) -> list[PersonalAccessToken]:
        """Return every token owned by one user."""
        raise NotImplementedError

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> PersonalAccessToken | None:
        """Return one token selected by its digest."""
        raise NotImplementedError

    async def get(self, *, token_id: str) -> PersonalAccessToken | None:
        """Return one token by its durable identifier."""
        raise NotImplementedError

    async def mark_used(self, *, token_id: str, used_at: datetime) -> None:
        """Record one successful token authentication."""
        raise NotImplementedError

    async def revoke(self, *, token_id: str, revoked_at: datetime) -> None:
        """Revoke one token."""
        raise NotImplementedError
