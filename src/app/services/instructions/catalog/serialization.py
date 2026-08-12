"""Serialization helpers for packaged instruction catalog metadata."""

from __future__ import annotations

import json
from typing import Any

from src.app.catalogs.instructions import (
    CatalogInstructionEntry,
    PersonaCatalogEntry,
    SkillCatalogEntry,
)


def serialize_catalog_metadata(entry: CatalogInstructionEntry) -> str:
    """Serialize non-relational metadata for one catalog instruction."""

    metadata: dict[str, Any] = {
        "applies_to": sorted(
            role.value
            for role in entry.metadata.applies_to
        ),
        "applies_when": list(entry.metadata.applies_when),
    }

    if isinstance(entry, SkillCatalogEntry):
        metadata.update(
            {
                "artifacts": [
                    artifact.value
                    for artifact in entry.artifacts
                ],
                "category": entry.category,
                "output": (
                    entry.output.value
                    if entry.output is not None
                    else None
                ),
                "phase": (
                    entry.phase.value
                    if entry.phase is not None
                    else None
                ),
                "reviewer_default_strictness": (
                    {
                        "prototype": (
                            entry.reviewer_default_strictness.prototype
                        ),
                        "mvp": entry.reviewer_default_strictness.mvp,
                        "production": (
                            entry.reviewer_default_strictness.production
                        ),
                    }
                    if entry.reviewer_default_strictness is not None
                    else None
                ),
            }
        )
    elif isinstance(entry, PersonaCatalogEntry):
        metadata["default_for"] = sorted(
            role.value
            for role in entry.default_for
        )

    return json.dumps(
        metadata,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
