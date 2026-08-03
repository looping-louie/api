"""Regression tests for public resource coverage in the API smoke script."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from src.app.main import app


HTTP_METHODS = frozenset({"delete", "get", "patch", "post", "put"})
EXCLUDED_PATH_PREFIXES = ("/api/v1/tasks",)
PATH_PARAMETERS = {
    "LOOP_ID": "loop_id",
    "LOOP_RUN_ID": "run_id",
    "model_id": "model_id",
    "PERSONA_ID": "persona_id",
    "PIPELINE_ID": "pipeline_id",
    "SMOKE_PROVIDER_ID": "provider_id",
    "SKILL_ID": "skill_id",
}
REQUEST_PATTERN = re.compile(
    r"\brequest(?:_expect_status)?\s+"
    r"(DELETE|GET|PATCH|POST|PUT)\s+"
    r'"([^"]+)"'
)


def test_smoke_script_references_every_public_resource_operation() -> None:
    """Every public CRUD-style resource operation has a smoke request."""
    script_path = _script_path()
    script = script_path.read_text(encoding="utf-8").replace("\\\n", " ")
    covered = {
        (method.lower(), _normalize_path(path))
        for method, path in REQUEST_PATTERN.findall(script)
    }
    documented = {
        (method, path.removeprefix("/api/v1"))
        for path, operations in app.openapi()["paths"].items()
        if not path.startswith(EXCLUDED_PATH_PREFIXES)
        for method in operations
        if method in HTTP_METHODS
    }

    assert documented <= covered


def test_failed_initial_request_does_not_modify_provider(
    tmp_path: Path,
) -> None:
    """Cleanup must not restore provider state that was never captured."""
    script_path = _script_path()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl_log = tmp_path / "curl.log"
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "${CURL_LOG}"\nexit 7\n',
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)
    environment = {
        **os.environ,
        "CURL_LOG": str(curl_log),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }

    result = subprocess.run(
        [str(script_path)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert curl_log.read_text(encoding="utf-8").count("--request") == 1


def _script_path() -> Path:
    """Return the repository smoke script path."""
    return Path(__file__).resolve().parents[1] / "scripts" / "smoke_api.sh"


def _normalize_path(path: str) -> str:
    """Convert one shell request path into its OpenAPI template form."""
    normalized = path.partition("?")[0]
    for shell_name, parameter_name in PATH_PARAMETERS.items():
        normalized = normalized.replace(
            f"${{{shell_name}}}",
            f"{{{parameter_name}}}",
        )
    return normalized
