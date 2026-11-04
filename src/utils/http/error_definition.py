"""Shared types for domain-to-HTTP error mappings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


ErrorDetails = dict[str, Any]
DetailsBuilder = Callable[[Exception], ErrorDetails | None]


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    """HTTP representation of a domain exception."""

    status_code: int
    code: str
    public_message: str | None = None
    details_builder: DetailsBuilder | None = None
