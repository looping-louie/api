"""Controllers for linked-service HTTP operations."""

from src.app.services.linked_services import LinkedServiceService

from .create import LinkedServiceCreateController
from .delete import LinkedServiceDeleteController
from .describe import LinkedServiceDescribeController
from .list import LinkedServiceListController
from .patch import LinkedServicePatchController


class LinkedServiceController(
    LinkedServiceCreateController,
    LinkedServiceDeleteController,
    LinkedServiceDescribeController,
    LinkedServiceListController,
    LinkedServicePatchController,
):
    """Compose endpoint-specific Linked Service controllers."""

    def __init__(self, *, linked_service_service: LinkedServiceService) -> None:
        """Store the linked-service application service."""

        self._linked_service_service = linked_service_service


__all__ = [
    'LinkedServiceController',
    'LinkedServiceCreateController',
    'LinkedServiceDeleteController',
    'LinkedServiceDescribeController',
    'LinkedServiceListController',
    'LinkedServicePatchController',
]
