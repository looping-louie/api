"""Translate FastAPI request validation failures to the API error envelope."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


ValidationItem = dict[str, Any]


def register_request_validation_handler(app: FastAPI) -> None:
    """Register the common Pydantic-to-envelope exception handler."""

    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )


async def request_validation_exception_handler(
    _request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    """Return a stable API envelope with useful safe Pydantic details."""

    errors = error.errors()
    code, message = _classification(errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": {
                    "errors": [_detail(item) for item in errors],
                },
            },
        },
    )


def _classification(
    errors: list[ValidationItem],
) -> tuple[str, str]:
    """Choose pipeline-specific codes before the generic request code."""

    if any(_is_unknown_step(item) for item in errors):
        return (
            "unsupported_pipeline_step",
            "The pipeline contains an unsupported step type.",
        )
    if any(_is_unknown_gate(item) for item in errors):
        return (
            "unsupported_human_gate_type",
            "The pipeline contains an unsupported human gate type.",
        )
    if any("steps" in item.get("loc", ()) for item in errors):
        return (
            "invalid_pipeline_steps",
            "The pipeline steps are invalid.",
        )
    return (
        "request_validation_error",
        "The request is invalid.",
    )


def _is_unknown_step(item: ValidationItem) -> bool:
    """Identify an invalid outer ``type`` discriminator."""

    if item.get("type") != "union_tag_invalid":
        return False
    if "steps" not in item.get("loc", ()):
        return False
    context = item.get("ctx", {})
    discriminator = str(context.get("discriminator", ""))
    return "type" in discriminator


def _is_unknown_gate(item: ValidationItem) -> bool:
    """Identify a rejected human-gate literal."""

    location = item.get("loc", ())
    return (
        item.get("type") == "literal_error"
        and "steps" in location
        and location[-1:] == ("gate_type",)
    )


def _detail(item: ValidationItem) -> ValidationItem:
    """Retain location, type, message, and serializable validation context."""

    detail: ValidationItem = {
        "loc": list(item.get("loc", ())),
        "type": item.get("type"),
        "message": item.get("msg"),
    }
    context = item.get("ctx")
    if context:
        detail["context"] = _json_safe(context)
    return detail


def _json_safe(value: object) -> object:
    """Convert Pydantic context values without exposing request input."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)
