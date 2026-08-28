"""Controllers for persona HTTP operations."""

from src.app.services.personas import PersonaService

from .create import PersonaCreateController
from .delete import PersonaDeleteController
from .describe import PersonaDescribeController
from .list import PersonaListController
from .patch import PersonaPatchController


class PersonaController(
    PersonaListController,
    PersonaDescribeController,
    PersonaCreateController,
    PersonaPatchController,
    PersonaDeleteController,
):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        """Store the shared persona application service."""
        self._persona_service = persona_service


__all__ = [
    "PersonaController",
    "PersonaCreateController",
    "PersonaDeleteController",
    "PersonaDescribeController",
    "PersonaListController",
    "PersonaPatchController",
]
