from __future__ import annotations

from typing import Mapping, Sequence

from src.app.catalogs.providers import ProviderId
from src.app.services.model_service import ProviderConnectionState


class FakeProviderStateRepository:
    """In-memory provider state repository."""

    def __init__(self) -> None:
        self._states: dict[
            tuple[str, ProviderId],
            ProviderConnectionState,
        ] = {}
        self.calls: list[
            tuple[str, tuple[ProviderId, ...]]
        ] = []

    def seed(
        self,
        *,
        workspace_id: str,
        state: ProviderConnectionState,
    ) -> None:
        """Register a provider state for one workspace."""

        self._states[
            (
                workspace_id,
                state.provider_id,
            )
        ] = state

    def remove(
        self,
        *,
        workspace_id: str,
        provider_id: ProviderId,
    ) -> None:
        """Remove a provider state."""

        self._states.pop(
            (
                workspace_id,
                provider_id,
            ),
            None,
        )

    async def get_states(
        self,
        *,
        workspace_id: str,
        provider_ids: Sequence[ProviderId],
    ) -> Mapping[ProviderId, ProviderConnectionState]:
        requested_ids = tuple(provider_ids)

        self.calls.append(
            (
                workspace_id,
                requested_ids,
            )
        )

        states: dict[
            ProviderId,
            ProviderConnectionState,
        ] = {}

        for provider_id in requested_ids:
            state = self._states.get(
                (
                    workspace_id,
                    provider_id,
                )
            )

            if state is not None:
                states[provider_id] = state

        return states
