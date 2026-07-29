#!/usr/bin/env python3
"""Fail CI when the packaged catalogs or runtime boundaries are invalid."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.app.catalogs.instructions.loader import load_instruction_catalog  # noqa: E402
from src.app.catalogs.loops import LOOP_CATALOG  # noqa: E402
from src.app.catalogs.models import MODEL_CATALOG  # noqa: E402
from src.app.catalogs.providers import PROVIDER_CATALOG  # noqa: E402


def main() -> None:
    """Validate every packaged catalog and print its inventory."""

    catalog = load_instruction_catalog()
    deployment_count = sum(
        len(model.deployments)
        for model in MODEL_CATALOG
    )
    print(
        "Catalog valid: "
        f"{len(PROVIDER_CATALOG)} providers, "
        f"{len(MODEL_CATALOG)} models, "
        f"{deployment_count} deployments, "
        f"{len(LOOP_CATALOG)} loops, "
        f"{len(catalog.skills)} skills, "
        f"{len(catalog.personas)} personas."
    )


if __name__ == "__main__":
    main()
