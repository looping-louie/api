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
    """Build response data, including the optional linked-service selection."""

    values = {
        field.name: getattr(document, field.name)
        for field in fields(document)
    }
    values['editable'] = document.editable
    values['duplicable'] = document.duplicable
    selection = document.linked_service_selection
    if selection is not None:
        values['linked_service'] = {
            'type': 'LinkedServiceReference',
            'reference_id': selection.linked_service_id,
        }
        values['config'] = {'model': selection.model_id}
    return values