"""Environment-backed application settings shared by feature services."""

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
    user_id: str
    builtin_skills_path: Path
    dev_auth_enabled: bool
    dev_user_id: str
    catalog_strict_versioning: bool


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
        user_id=os.getenv("LOUIE_USER_ID", "local-user"),
        builtin_skills_path=_resolve_builtin_skills_path(),
        dev_auth_enabled=_environment_flag(
            "LOUIE_DEV_AUTH",
        ),
        dev_user_id=os.getenv(
            "LOUIE_DEV_USER_ID",
            "local-user",
            ).strip(),
        catalog_strict_versioning=_environment_flag(
            "LOUIE_CATALOG_STRICT_VERSIONING",
        ),
    )


def _environment_flag(name: str) -> bool:
    """Return whether an environment flag is enabled."""

    return os.getenv(
        name,
        "",
    ).strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _resolve_builtin_skills_path() -> Path:
    """Resolve the version-controlled built-in skills directory."""

    configured = _optional_environment_value(
        "LOUIE_BUILTIN_SKILLS_PATH"
    )

    if configured is not None:
        return Path(configured)

    candidates = (
        Path("src/app/catalogs/skills"),
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
