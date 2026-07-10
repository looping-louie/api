"""Generator-related schemas."""

from pydantic import BaseModel


class GeneratorAssignment(BaseModel):
    """
    Generator configuration selected for one task.

    The persona determines how the generator approaches the work. Skills add
    task-specific technical knowledge, and focus narrows the assignment.
    """

    persona: str
    skills: list[str]
    focus: str


__all__ = ['GeneratorAssignment']
