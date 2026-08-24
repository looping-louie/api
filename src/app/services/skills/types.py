"""Skill lifecycle input contracts."""

from __future__ import annotations

from dataclasses import dataclass

from ..instructions import DefinitionCreate, DefinitionUpdate


@dataclass(frozen=True, slots=True)
class SkillCreate(DefinitionCreate):
    """Content required to create a Skill."""


@dataclass(frozen=True, slots=True)
class SkillUpdate(DefinitionUpdate):
    """Partial content changes applied to a Skill."""
