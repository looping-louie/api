"""Loader for packaged persona definitions."""

from pathlib import Path
from typing import Any

from src.app.catalogs._resource_loader import (
    load_content,
    load_registry,
)
from src.app.catalogs.instructions import CatalogInstructionType


PERSONA_CATALOG_DIR = Path(__file__).parent


def load_persona_catalog() -> list[dict[str, Any]]:
    """Load persona metadata from its explicit manifest."""

    return load_registry(
        catalog_dir=PERSONA_CATALOG_DIR,
        instruction_type=CatalogInstructionType.PERSONA,
    )


def load_persona_content(persona_id_or_key: str) -> str:
    """Load one persona using its stable ID or temporary legacy key."""

    return load_content(
        catalog_dir=PERSONA_CATALOG_DIR,
        registry=load_persona_catalog(),
        instruction_id_or_key=persona_id_or_key,
    )
