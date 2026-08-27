"""Domain model for projects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class ProjectDocument:
    """Project identity and metadata visible to its members."""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime
