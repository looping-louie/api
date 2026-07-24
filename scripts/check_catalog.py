#!/usr/bin/env python3
"""Fail CI when the packaged catalogs or runtime boundaries are invalid."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "src" / "app"
sys.path.insert(0, str(ROOT))

from src.app.catalogs.loader import load_instruction_catalog  # noqa: E402
from src.app.catalogs.loops import LOOP_CATALOG  # noqa: E402
from src.app.catalogs.models import MODEL_CATALOG  # noqa: E402
from src.app.catalogs.providers import PROVIDER_CATALOG  # noqa: E402


BANNED_IMPORTS = (
    "src.app.skills",
    "src.app.personas",
)


def main() -> None:
    catalog = load_instruction_catalog()
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in APP_DIR.rglob("*.py")
    )

    for banned_import in BANNED_IMPORTS:
        if banned_import in source:
            raise SystemExit(
                f"Runtime still imports removed package: {banned_import}"
            )

    for removed_directory in ("skills", "personas"):
        path = APP_DIR / removed_directory
        if path.exists():
            raise SystemExit(f"Legacy runtime directory still exists: {path}")

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
