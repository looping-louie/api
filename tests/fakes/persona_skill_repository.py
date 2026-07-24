"""In-memory persona-skill persistence for service tests."""

from collections.abc import Sequence


class FakePersonaSkillRepository:
    """Store ordered persona-skill associations in memory."""

    def __init__(self) -> None:
        """Initialize an empty association store."""

        self._skill_ids_by_persona: dict[str, tuple[str, ...]] = {}

    async def list_for_persona(self, *, persona_id: str) -> tuple[str, ...]:
        """Return associated skills in their declared order."""

        return self._skill_ids_by_persona.get(persona_id, ())

    async def replace_for_persona(
        self,
        *,
        persona_id: str,
        skill_ids: Sequence[str],
    ) -> None:
        """Replace every skill associated with a persona."""

        self._skill_ids_by_persona[persona_id] = tuple(skill_ids)

    def remove_skill(self, *, skill_id: str) -> None:
        """Simulate database cascading after a skill deletion."""

        for persona_id, skill_ids in self._skill_ids_by_persona.items():
            self._skill_ids_by_persona[persona_id] = tuple(
                candidate
                for candidate in skill_ids
                if candidate != skill_id
            )
