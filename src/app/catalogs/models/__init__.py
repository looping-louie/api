"""Public curated logical model catalog and contracts."""

from .items import MODEL_ITEMS
from .types import (
    ModelCapability,
    ModelCatalogEntry,
    ModelCatalogValidationError,
    ModelDeployment,
    ModelEndpoint,
    ModelLab,
    ModelPricing,
    ModelSort,
    ModelStatus,
)
from .validation import validate_model_catalog


MODEL_CATALOG = MODEL_ITEMS

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
    "ModelLab",
    "ModelPricing",
    "ModelSort",
    "ModelStatus",
    "validate_model_catalog",
]
