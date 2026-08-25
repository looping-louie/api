"""Shared domain values used to configure model execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelTarget:
    """One provider connection and logical model selected for execution."""

    linked_service_id: str
    model_id: str
