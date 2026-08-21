"""In-memory persistence for persona linked-service selections."""

from src.app.services.personas import PersonaLinkedServiceSelection


class FakePersonaLinkedServiceSelectionRepository:
    """Store one linked-service selection for each workspace persona."""

    def __init__(self) -> None:
        """Initialize an empty selection store."""

        self._selection_by_persona: dict[
            tuple[str, str], PersonaLinkedServiceSelection
        ] = {}

    async def get_for_persona(
        self,
        *,
        workspace_id: str,
        persona_id: str,
    ) -> PersonaLinkedServiceSelection | None:
        """Return the stored selection identifier when one exists."""

        return self._selection_by_persona.get((workspace_id, persona_id))

    async def replace_for_persona(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        selection: PersonaLinkedServiceSelection,
    ) -> None:
        """Store or remove the optional linked-service selection."""

        self._selection_by_persona[(workspace_id, persona_id)] = selection
