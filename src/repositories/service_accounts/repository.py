"""Persistence contract for runtime service accounts."""

from datetime import datetime
from typing import Protocol

from src.models.service_account import ServiceAccount


class ServiceAccountRepository(Protocol):
    """Persist project-scoped service-account credentials."""

    async def create(self, account: ServiceAccount) -> ServiceAccount:
        """Store one service account with project bindings."""
        raise NotImplementedError

    async def list_for_administrator(
        self,
        *,
        administrator_id: str,
    ) -> list[ServiceAccount]:
        """Return accounts administered by one user."""
        raise NotImplementedError

    async def get(self, *, account_id: str) -> ServiceAccount | None:
        """Return one service account by durable ID."""
        raise NotImplementedError

    async def revoke(self, *, account_id: str, revoked_at: datetime) -> None:
        """Revoke one account without deleting its audit record."""
        raise NotImplementedError
