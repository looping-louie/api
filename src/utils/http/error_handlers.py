"""Register and serve domain-to-HTTP exception mappings."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .domain_error_definitions import ERROR_DEFINITIONS
from .request_validation import register_request_validation_handler


async def domain_exception_handler(
    _request: Request,
    error: Exception,
) -> JSONResponse:
    """Convert a known domain exception into a consistent HTTP response."""

    definition = ERROR_DEFINITIONS.get(type(error))

    if definition is None:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                    "details": None,
                },
            },
        )

    details = None

    if definition.details_builder is not None:
        details = definition.details_builder(error)

    return JSONResponse(
        status_code=definition.status_code,
        content={
            "error": {
                "code": definition.code,
                "message": definition.public_message or str(error),
                "details": details,
            },
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register every domain-to-HTTP exception mapping."""

    register_request_validation_handler(app)
    for error_type in ERROR_DEFINITIONS:
        app.add_exception_handler(
            error_type,
            domain_exception_handler,
        )
