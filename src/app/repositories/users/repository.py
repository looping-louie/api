"""Persistence contract for user identities."""

from typing import Protocol

from src.app.models.user import UserDocument


class UserRepository(Protocol):
    """Persist durable API user identities."""

    async def get(self, *, user_id: str) -> UserDocument | None:
        """Return one user by its external identity."""
        raise NotImplementedError

    async def create_if_absent(self, document: UserDocument) -> UserDocument:
        """Create a user or return its existing durable record."""
        raise NotImplementedError
