"""Loader for packaged skill definitions."""

from pathlib import Path
from typing import Any

from src.app.catalogs._resource_loader import (
    load_content,
    load_registry,
)
from src.app.catalogs.instructions import CatalogInstructionType


SKILL_CATALOG_DIR = Path(__file__).parent


def load_skill_catalog() -> list[dict[str, Any]]:
    """Load skill metadata from its explicit manifest."""

    return load_registry(
        catalog_dir=SKILL_CATALOG_DIR,
        instruction_type=CatalogInstructionType.SKILL,
    )


def load_skill_content(skill_id_or_key: str) -> str:
    """Load one skill using its stable ID or temporary legacy key."""

    return load_content(
        catalog_dir=SKILL_CATALOG_DIR,
        registry=load_skill_catalog(),
        instruction_id_or_key=skill_id_or_key,
    )
