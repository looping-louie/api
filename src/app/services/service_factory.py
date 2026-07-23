"""Factories for application services and shared infrastructure."""

from functools import lru_cache

from src.app.catalogs.providers import PROVIDER_CATALOG
from src.app.repositories.provider_repository import (
    SqliteProviderRepository,
)
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


@lru_cache(maxsize=1)
def get_database() -> SqliteDatabase:
    """Return the process-wide SQLite database object."""

    settings = get_app_settings()

    return SqliteDatabase(settings.database_path)


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
        catalog=PROVIDER_CATALOG,
        request_context=get_request_context(),
    )
