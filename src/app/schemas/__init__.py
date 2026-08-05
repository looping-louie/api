"""
Public API schemas.

These models define the contract between the HTTP API and clients.

The runner internally exchanges richer Python objects, but every request
and response crossing the API boundary is validated through these schemas.

The hierarchy is intentionally split into:
- requests
- metrics
- reviewer results
- execution trace
- run response
"""

from src.app.schemas.project import ProjectProfile, ProjectProfileMarkers

__all__ = [
    'ProjectProfile',
    'ProjectProfileMarkers',
]
