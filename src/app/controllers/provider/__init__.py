"""Controllers for model provider HTTP operations."""

from src.app.services.providers.provider_service import ProviderService

from .delete import ProviderDeleteController
from .describe import ProviderDescribeController
from .list import ProviderListController
from .patch import ProviderPatchController


class ProviderController(
    ProviderListController,
    ProviderDescribeController,
    ProviderPatchController,
    ProviderDeleteController,
):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(self, *, provider_service: ProviderService) -> None:
        """Store the shared provider application service."""
        self._provider_service = provider_service


__all__ = [
    "ProviderController",
    "ProviderDeleteController",
    "ProviderDescribeController",
    "ProviderListController",
    "ProviderPatchController",
]
