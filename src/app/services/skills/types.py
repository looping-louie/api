"""Skill lifecycle input contracts."""

from __future__ import annotations

from dataclasses import dataclass

from ..instructions import InstructionCreate, InstructionUpdate


@dataclass(frozen=True, slots=True)
class SkillCreate(InstructionCreate):
    """Content required to create a Skill."""


@dataclass(frozen=True, slots=True)
class SkillUpdate(InstructionUpdate):
    """Partial content changes applied to a Skill."""