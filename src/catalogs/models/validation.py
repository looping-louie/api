"""Consistency validation for curated logical model catalogs."""

import re
from collections.abc import Sequence
from datetime import date

from ..providers import PROVIDER_CATALOG, ProviderCatalogEntry, ProviderId
from .types import ModelCatalogEntry, ModelCatalogValidationError, ModelLab


_MODEL_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")


def validate_model_catalog(
    catalog: Sequence[ModelCatalogEntry],
    *,
    provider_catalog: Sequence[ProviderCatalogEntry] = PROVIDER_CATALOG,
) -> None:
    """Validate logical models and provider-owned offering routes."""

    known_provider_ids = {provider.id for provider in provider_catalog}
    seen_model_ids: set[str] = set()
    deployment_owners: dict[tuple[ProviderId, str], str] = {}

    for model in catalog:
        if not isinstance(model.id, str) or not _MODEL_ID_PATTERN.fullmatch(
            model.id
        ):
            raise ModelCatalogValidationError(
                f"Invalid model catalog id '{model.id}'."
            )

        if model.id in seen_model_ids:
            raise ModelCatalogValidationError(
                f"Duplicate model catalog id '{model.id}'."
            )

        if not isinstance(model.released_at, date):
            raise ModelCatalogValidationError(
                f"Model '{model.id}' must define a valid release date."
            )

        if not isinstance(model.lab, ModelLab):
            raise ModelCatalogValidationError(
                f"Model '{model.id}' references unknown lab "
                f"'{model.lab}'."
            )

        seen_model_ids.add(model.id)

    for provider in provider_catalog:
        if provider.id not in known_provider_ids:
            raise ModelCatalogValidationError(
                f"Unknown provider '{provider.id}'."
            )
        for offering in provider.offerings:
            if offering.model_id not in seen_model_ids:
                raise ModelCatalogValidationError(
                    f"Provider '{provider.id}' references unknown model "
                    f"'{offering.model_id}'."
                )

            provider_model_id = offering.provider_model_id
            if (
                not isinstance(provider_model_id, str)
                or not provider_model_id.strip()
                or provider_model_id != provider_model_id.strip()
            ):
                raise ModelCatalogValidationError(
                    f"Provider '{provider.id}' has an invalid provider model id."
                )

            deployment_key = (provider.id, provider_model_id)
            current_owner = deployment_owners.get(deployment_key)
            if current_owner is not None:
                raise ModelCatalogValidationError(
                    "Duplicate model deployment "
                    f"'{provider.id.value}:"
                    f"{provider_model_id}' in models "
                        f"'{current_owner}' and '{offering.model_id}'."
                )

            deployment_owners[deployment_key] = offering.model_id

    offered_model_ids = set(deployment_owners.values())
    for model in catalog:
        if model.id not in offered_model_ids:
            raise ModelCatalogValidationError(
                f"Model '{model.id}' must define at least one offering."
            )

    for model in catalog:
        replacement_id = model.replacement_model_id
        if (
            replacement_id is not None
            and replacement_id not in seen_model_ids
        ):
            raise ModelCatalogValidationError(
                f"Model '{model.id}' references missing replacement "
                f"'{replacement_id}'."
            )
