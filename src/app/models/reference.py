"""Domain values for references and dependency relationships."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourceReference:
    """Reference to a domain resource belonging to a workspace."""

    resource_type: str
    resource_id: str


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    """Reference paired with its resolved domain value."""

    reference: ResourceReference
    value: object


@dataclass(frozen=True, slots=True)
class DependencyUsage:
    """Resource that depends on another workspace resource."""

    source: ResourceReference
    relation: str
    blocking: bool = True