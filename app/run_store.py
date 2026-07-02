"""
Run persistence helpers.

Every harness execution produces prompts, responses, diffs, metrics and
other debugging artefacts.

This module provides small utilities to persist those artefacts inside
the run directory under .looping-louie/runs/<run_id>/.
"""

import json
from pathlib import Path
from typing import Any

# TODO:
# Introduce a retention policy to automatically remove old run folders
# after a configurable number of days or executions.

# TODO:
# Support serialising Pydantic models transparently instead of requiring
# callers to convert them to dictionaries beforehand.
def write_json(run_path: Path, filename: str, data: Any) -> None:
    """
    Serialize an object as formatted JSON inside the current run directory.
    """
    path = run_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

def write_text(run_path: Path, filename: str, content: str) -> None:
    """
    Persist plain text content inside the current run directory.
    """
    path = run_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")