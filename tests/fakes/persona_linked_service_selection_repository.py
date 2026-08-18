"""In-memory persistence for persona linked-service selections."""

from src.app.services.personas import PersonaLinkedServiceSelection


class FakePersonaLinkedServiceSelectionRepository:
    """Store one optional linked-service selection for each persona in memory."""

    def __init__(self) -> None:
        """Initialize an empty selection store."""

        self._selection_by_persona: dict[str, PersonaLinkedServiceSelection] = {}

    async def get_for_persona(
        self,
        *,
        persona_id: str,
    ) -> PersonaLinkedServiceSelection | None:
        """Return the stored selection identifier when one exists."""

        return self._selection_by_persona.get(persona_id)

    async def replace_for_persona(
        self,
        *,
        persona_id: str,
        selection: PersonaLinkedServiceSelection | None,
    ) -> None:
        """Store or remove the optional linked-service selection."""

        if selection is None:
            self._selection_by_persona.pop(persona_id, None)
            return
        self._selection_by_persona[persona_id] = selection
