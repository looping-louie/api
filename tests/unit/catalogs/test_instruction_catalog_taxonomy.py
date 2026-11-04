"""Contract tests for the shared instruction business taxonomy."""

from src.catalogs.persona_skills import CatalogInstructionCategory
from src.catalogs.personas.loader import load_persona_catalog
from src.catalogs.skills.loader import load_skill_catalog


def test_packaged_instructions_use_the_stable_business_taxonomy() -> None:
    """Every packaged skill and persona uses one of twelve categories."""

    skills = load_skill_catalog()
    personas = load_persona_catalog()

    assert len(CatalogInstructionCategory) == 12
    assert all(
        isinstance(entry.category, CatalogInstructionCategory)
        for entry in (*skills, *personas)
    )
