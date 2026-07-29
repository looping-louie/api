"""Consistency validation for curated logical model catalogs."""

import re
from collections.abc import Sequence

from ..providers import PROVIDER_CATALOG, ProviderCatalogEntry, ProviderId
from .types import (
    ModelCatalogEntry,
    ModelCatalogValidationError,
)


_MODEL_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")


def validate_model_catalog(
    catalog: Sequence[ModelCatalogEntry],
    *,
    provider_catalog: Sequence[ProviderCatalogEntry] = PROVIDER_CATALOG,
) -> None:
    """Validate model identities and provider deployment routes."""

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

        if not model.deployments:
            raise ModelCatalogValidationError(
                f"Model '{model.id}' must define at least one deployment."
            )

        seen_model_ids.add(model.id)

        for deployment in model.deployments:
            if (
                not isinstance(deployment.provider_id, ProviderId)
                or deployment.provider_id not in known_provider_ids
            ):
                raise ModelCatalogValidationError(
                    f"Model '{model.id}' references unknown provider "
                    f"'{deployment.provider_id}'."
                )

            provider_model_id = deployment.provider_model_id
            if (
                not isinstance(provider_model_id, str)
                or not provider_model_id.strip()
                or provider_model_id != provider_model_id.strip()
            ):
                raise ModelCatalogValidationError(
                    f"Model '{model.id}' has an invalid provider model id."
                )

            deployment_key = (deployment.provider_id, provider_model_id)
            current_owner = deployment_owners.get(deployment_key)
            if current_owner is not None:
                raise ModelCatalogValidationError(
                    "Duplicate model deployment "
                    f"'{deployment.provider_id.value}:"
                    f"{provider_model_id}' in models "
                    f"'{current_owner}' and '{model.id}'."
                )

            deployment_owners[deployment_key] = model.id

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
