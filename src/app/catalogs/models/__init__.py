"""Public curated logical model catalog and contracts."""

from .items import MODEL_ITEMS
from .index import CatalogIndex
from .types import (
    ModelCapability,
    ModelCatalogEntry,
    ModelCatalogValidationError,
    ModelEndpoint,
    ModelLab,
    ModelOffering,
    ModelPricing,
    ProviderModelOffering,
    ModelSort,
    ModelStatus,
)
from .validation import validate_model_catalog
from ..providers import PROVIDER_CATALOG


MODEL_CATALOG = MODEL_ITEMS

validate_model_catalog(MODEL_CATALOG)

CATALOG_INDEX = CatalogIndex(
    models=MODEL_CATALOG,
    providers=PROVIDER_CATALOG,
)


MODEL_CATALOG_BY_ID: dict[str, ModelCatalogEntry] = {
    model.id: model
    for model in MODEL_CATALOG
}


__all__ = [
    "MODEL_CATALOG",
    "MODEL_CATALOG_BY_ID",
    "CATALOG_INDEX",
    "CatalogIndex",
    "ModelCapability",
    "ModelCatalogEntry",
    "ModelCatalogValidationError",
    "ModelEndpoint",
    "ModelLab",
    "ModelOffering",
    "ModelPricing",
    "ProviderModelOffering",
    "ModelSort",
    "ModelStatus",
    "validate_model_catalog",
]
