"""Environment-backed settings used by provider services."""

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(".env.local", override=False)
load_dotenv(".env", override=False)


@dataclass(frozen=True)
class ProviderSettings:
    """Configuration required by the provider feature."""

    encryption_key: str
    database_path: Path
    org_id: str
    user_id: str
    model_counts: dict[str, int]


@lru_cache(maxsize=1)
def get_provider_settings() -> ProviderSettings:
    """Load and validate provider settings once per application process."""

    encryption_key = os.getenv("LOUIE_ENCRYPTION_KEY", "").strip()

    if not encryption_key:
        raise RuntimeError(
            "LOUIE_ENCRYPTION_KEY is required. Generate one with Fernet."
        )

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

    model_counts = {
        str(provider): max(0, int(count))
        for provider, count in parsed_counts.items()
    }

    return ProviderSettings(
        encryption_key=encryption_key,
        database_path=Path(
            os.getenv(
                "LOUIE_DB_PATH",
                ".looping-louie/data/looping-louie.db",
            )
        ),
        org_id=os.getenv("LOUIE_ORG_ID", "local-org"),
        user_id=os.getenv("LOUIE_USER_ID", "local-user"),
        model_counts=model_counts,
    )
