"""Application service for API user identity profiles."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from src.app.models.user import UserDocument
from src.app.repositories.users import UserRepository


class UserNotFoundError(Exception):
    """Raised when an identified user has not registered a profile."""

    def __init__(self, user_id: str) -> None:
        """Store the absent user identity."""

        super().__init__(f"User '{user_id}' was not found.")
        self.user_id = user_id


class UserService:
    """Create and retrieve durable profiles for request identities."""

    def __init__(
        self,
        *,
        repository: UserRepository,
        clock: Callable[[], datetime],
    ) -> None:
        """Store user persistence and the application clock."""

        self._repository = repository
        self._clock = clock

    async def get(self, *, user_id: str) -> UserDocument:
        """Return the registered profile for one request identity."""

        normalized_user_id = _require_user_id(user_id)
        document = await self._repository.get(user_id=normalized_user_id)
        if document is None:
            raise UserNotFoundError(normalized_user_id)
        return document

    async def register(self, *, user_id: str) -> UserDocument:
        """Ensure that one request identity has a durable profile."""

        normalized_user_id = _require_user_id(user_id)
        now = self._clock()
        return await self._repository.create_if_absent(UserDocument(
            id=normalized_user_id,
            created_at=now,
            updated_at=now,
        ))


def _require_user_id(value: str) -> str:
    """Normalize one required external user identity."""

    normalized = value.strip()
    if not normalized:
        raise ValueError('user_id must be non-empty.')
    return normalized