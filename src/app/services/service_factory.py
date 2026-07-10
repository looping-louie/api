"""Factories for application services and shared infrastructure."""

from functools import lru_cache

from src.app.repositories.provider_repository import (
    SqliteProviderRepository,
)
from src.app.repositories.skill_repository import SqliteSkillRepository
from src.app.repositories.sqlite_database import SqliteDatabase
from src.app.services.app_settings_service import get_app_settings
from src.app.services.providers.model_registry_service import (
    StaticModelRegistryService,
)
from src.app.services.providers.provider_connection_service import (
    HttpProviderConnectionService,
)
from src.app.services.providers.provider_service import ProviderService
from src.app.services.providers.request_context_service import (
    EnvironmentRequestContextService,
)
from src.app.services.providers.secret_service import FernetSecretService
from src.app.services.skills.skill_document_service import SkillDocumentService
from src.app.services.skills.skill_service import SkillService


@lru_cache(maxsize=1)
def get_database() -> SqliteDatabase:
    """Return the process-wide SQLite database object."""

    settings = get_app_settings()

    return SqliteDatabase(settings.database_path)


@lru_cache(maxsize=1)
def get_request_context() -> EnvironmentRequestContextService:
    """Return the current development request context."""

    settings = get_app_settings()

    return EnvironmentRequestContextService(
        org_id=settings.org_id,
        user_id=settings.user_id,
    )


@lru_cache(maxsize=1)
def get_provider_service() -> ProviderService:
    """Build ProviderService with concrete dependencies."""

    settings = get_app_settings()

    if settings.encryption_key is None:
        raise RuntimeError("LOUIE_ENCRYPTION_KEY is required.")

    return ProviderService(
        repository=SqliteProviderRepository(get_database()),
        secret_service=FernetSecretService(
            settings.encryption_key
        ),
        connection_service=HttpProviderConnectionService(),
        model_registry=StaticModelRegistryService(
            counts=settings.model_counts
        ),
        request_context=get_request_context(),
    )


@lru_cache(maxsize=1)
def get_skill_service() -> SkillService:
    """Build SkillService with concrete dependencies."""

    settings = get_app_settings()

    return SkillService(
        repository=SqliteSkillRepository(get_database()),
        document_service=SkillDocumentService(
            settings.builtin_skills_path
        ),
        request_context=get_request_context(),
    )
