"""In-memory persistence for optional persona-model associations."""


class FakePersonaModelRepository:
    """Store one optional model ID for each persona in memory."""

    def __init__(self) -> None:
        """Initialize an empty association store."""

        self._model_id_by_persona: dict[str, str] = {}

    async def get_for_persona(self, *, persona_id: str) -> str | None:
        """Return the stored model identifier when one exists."""

        return self._model_id_by_persona.get(persona_id)

    async def replace_for_persona(
        self,
        *,
        persona_id: str,
        model_id: str | None,
    ) -> None:
        """Store or remove the optional model association."""

        if model_id is None:
            self._model_id_by_persona.pop(persona_id, None)
            return
        self._model_id_by_persona[persona_id] = model_id