"""Persona HTTP response conversion."""

from dataclasses import fields

from src.app.schemas.persona import PersonaResponse, PersonaSummaryResponse
from src.app.services.personas.types import (
    AvailablePersonaSummary,
    PersonaResultDocument,
)


def persona_response(document: PersonaResultDocument) -> PersonaResponse:
    """Convert a complete persona document into its HTTP representation."""

    return PersonaResponse.model_validate(_response_values(document))


def persona_summary_response(
    document: AvailablePersonaSummary,
) -> PersonaSummaryResponse:
    """Convert a persona summary into its HTTP representation."""

    return PersonaSummaryResponse.model_validate(_response_values(document))


def _response_values(
    document: PersonaResultDocument | AvailablePersonaSummary,
) -> dict[str, object]:
    """Build response data from a persona document."""

    values = {
        field.name: getattr(document, field.name)
        for field in fields(document)
    }
    values['editable'] = document.editable
    values['duplicable'] = document.duplicable
    return values
