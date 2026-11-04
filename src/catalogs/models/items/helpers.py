"""Construction helpers shared by curated model data modules."""

from datetime import date
from decimal import Decimal

from ..types import ModelCapability, ModelPricing


def _pricing(
    input_price: str,
    output_price: str,
    cached_input_price: str | None = None,
    *,
    valid_until: date | None = None,
    note: str | None = None,
) -> ModelPricing:
    """Convert decimal price literals into one deployment price record."""

    return ModelPricing(
        input_per_million_usd=Decimal(input_price),
        output_per_million_usd=Decimal(output_price),
        cached_input_per_million_usd=(
            Decimal(cached_input_price)
            if cached_input_price is not None
            else None
        ),
        valid_until=valid_until,
        note=note,
    )


TEXT = frozenset({ModelCapability.TEXT})

GENERAL_REASONING = frozenset(
    {
        ModelCapability.TEXT,
        ModelCapability.VISION,
        ModelCapability.REASONING,
        ModelCapability.FUNCTION_CALLING,
        ModelCapability.STRUCTURED_OUTPUT,
        ModelCapability.CODING,
    }
)
