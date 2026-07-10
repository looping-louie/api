"""Current request identity abstraction."""

from typing import Protocol

from src.app.models.providers import RequestActor


class RequestContextService(Protocol):
    """Returns the actor associated with the current request."""

    def get_current_actor(self) -> RequestActor:
        """Return the current organisation and user."""


class EnvironmentRequestContextService:
    """Development request context backed by process settings."""

    def __init__(self, org_id: str, user_id: str) -> None:
        """Store the local organisation and user identifiers."""

        self._actor = RequestActor(
            org_id=org_id,
            user_id=user_id,
        )

    def get_current_actor(self) -> RequestActor:
        """Return the configured local actor."""

        return self._actor
