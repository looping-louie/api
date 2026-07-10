"""Environment-backed application settings shared by feature services."""

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(".env.local", override=False)
load_dotenv(".env", override=False)


@dataclass(frozen=True)
class AppSettings:
    """Settings shared by provider and skill features."""

    encryption_key: str | None
    database_path: Path
    org_id: str
    user_id: str
    model_counts: dict[str, int]
    builtin_skills_path: Path


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Load application settings once per process."""

    return AppSettings(
        encryption_key=_optional_environment_value(
            "LOUIE_ENCRYPTION_KEY"
        ),
        database_path=Path(
            os.getenv(
                "LOUIE_DB_PATH",
                ".looping-louie/data/looping-louie.db",
            )
        ),
        org_id=os.getenv("LOUIE_ORG_ID", "local-org"),
        user_id=os.getenv("LOUIE_USER_ID", "local-user"),
        model_counts=_load_provider_model_counts(),
        builtin_skills_path=_resolve_builtin_skills_path(),
    )


def _load_provider_model_counts() -> dict[str, int]:
    """Parse provider model counts from JSON configuration."""

    raw_counts = os.getenv("LOUIE_PROVIDER_MODEL_COUNTS", "{}")

    try:
        parsed_counts = json.loads(raw_counts)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "LOUIE_PROVIDER_MODEL_COUNTS must be a JSON object."
        ) from exc

    if not isinstance(parsed_counts, dict):
        raise RuntimeError(
            "LOUIE_PROVIDER_MODEL_COUNTS must be a JSON object."
        )

    return {
        str(provider): max(0, int(count))
        for provider, count in parsed_counts.items()
    }


def _resolve_builtin_skills_path() -> Path:
    """Resolve the version-controlled built-in skills directory."""

    configured = _optional_environment_value(
        "LOUIE_BUILTIN_SKILLS_PATH"
    )

    if configured is not None:
        return Path(configured)

    candidates = (
        Path("src/app/skills"),
        Path("src/app/resources/skills"),
        Path("skills"),
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def _optional_environment_value(name: str) -> str | None:
    """Return one trimmed environment value or None."""

    value = os.getenv(name, "").strip()

    return value or None
