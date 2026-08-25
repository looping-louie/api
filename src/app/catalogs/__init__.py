"""Convenient access to the combined Persona and Skill catalog."""

from .persona_skills import InstructionOrigin
from .persona_skills.loader import load_persona_skill_catalog


__all__ = [
    "InstructionOrigin",
    "load_persona_skill_catalog",
]
