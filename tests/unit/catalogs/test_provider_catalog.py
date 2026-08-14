from dataclasses import FrozenInstanceError

import pytest

from src.app.catalogs.providers import (
    PROVIDER_CATALOG,
    PROVIDER_CATALOG_BY_ID,
    ProviderId,
)


def test_provider_catalog_has_one_entry_for_every_provider_id() -> None:
    assert tuple(
        entry.id
        for entry in PROVIDER_CATALOG
    ) == tuple(ProviderId)
    assert set(PROVIDER_CATALOG_BY_ID) == set(ProviderId)


def test_provider_catalog_entries_are_immutable() -> None:
    provider = PROVIDER_CATALOG_BY_ID[ProviderId.OPENAI]

    with pytest.raises(FrozenInstanceError):
        provider.name = "Changed"  # type: ignore[misc]
