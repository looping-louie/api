"""Combined typed loader for packaged Persona and Skill definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .entries import (
    CatalogInstructionEntry,
    PersonaCatalogEntry,
    SkillCatalogEntry,
)
from .errors import CatalogLoadError
from ..personas.loader import (
    PERSONA_CATALOG_DIR,
    load_persona_catalog,
)
from ..skills.loader import (
    SKILL_CATALOG_DIR,
    load_skill_catalog,
)


@dataclass(frozen=True, slots=True)
class PersonaSkillCatalog:
    """Immutable Persona and Skill catalog loaded as one unit."""

    skills: tuple[SkillCatalogEntry, ...]
    personas: tuple[PersonaCatalogEntry, ...]

    @property
    def entries(self) -> tuple[CatalogInstructionEntry, ...]:
        """Return every definition in deterministic catalog order."""

        return (*self.skills, *self.personas)


def load_persona_skill_catalog(
    *,
    skill_catalog_dir: Path = SKILL_CATALOG_DIR,
    persona_catalog_dir: Path = PERSONA_CATALOG_DIR,
) -> PersonaSkillCatalog:
    """Load Persona and Skill catalogs and validate their cross-references."""

    skills = load_skill_catalog(skill_catalog_dir)
    personas = load_persona_catalog(persona_catalog_dir)
    skill_ids = {
        skill.id
        for skill in skills
    }
    all_ids: set[str] = set()

    for entry in (*skills, *personas):
        if entry.id in all_ids:
            raise CatalogLoadError(
                f"Duplicate Persona and Skill catalog id: {entry.id}"
            )

        all_ids.add(entry.id)

    for persona in personas:
        missing_skill_ids = [
            skill_id
            for skill_id in persona.skill_ids
            if skill_id not in skill_ids
        ]

        if missing_skill_ids:
            raise CatalogLoadError(
                f"Persona '{persona.id}' references unknown associated "
                f"skills: {sorted(missing_skill_ids)}."
            )

    return PersonaSkillCatalog(
        skills=skills,
        personas=personas,
    )
