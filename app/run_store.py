import json
from pathlib import Path
from typing import Any


def write_json(run_path: Path, filename: str, data: Any) -> None:
    path = run_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def write_text(run_path: Path, filename: str, content: str) -> None:
    path = run_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")