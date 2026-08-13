"""Public curated logical model catalog and contracts."""

from .nvidia import NVIDIA_MODEL_CATALOG
from .primary import PRIMARY_MODEL_CATALOG
from .secondary import SECONDARY_MODEL_CATALOG
from .types import (
    ModelCapability,
    ModelCatalogEntry,
    ModelCatalogValidationError,
    ModelDeployment,
    ModelEndpoint,
    ModelPricing,
    ModelSort,
    ModelStatus,
)
from .validation import validate_model_catalog


MODEL_CATALOG = (
    PRIMARY_MODEL_CATALOG
    + SECONDARY_MODEL_CATALOG
    + NVIDIA_MODEL_CATALOG
)

validate_model_catalog(MODEL_CATALOG)

MODEL_CATALOG_BY_ID: dict[str, ModelCatalogEntry] = {
    model.id: model
    for model in MODEL_CATALOG
}


__all__ = [
    "MODEL_CATALOG",
    "MODEL_CATALOG_BY_ID",
    "ModelCapability",
    "ModelCatalogEntry",
    "ModelCatalogValidationError",
    "ModelDeployment",
    "ModelEndpoint",
    "ModelPricing",
    "ModelSort",
    "ModelStatus",
    "validate_model_catalog",
]
