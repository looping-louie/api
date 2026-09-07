"""HTTP schemas shared by execution configuration scopes."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .shared import NonEmptyString, RequestSchema, ResponseSchema


class HarnessRequest(RequestSchema):
    """One supported local execution mechanism."""

    kind: Literal['louie', 'codex_cli', 'copilot_cli'] = 'louie'
    version: Literal['v1'] = 'v1'
    config: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode='after')
    def require_empty_config(self) -> 'HarnessRequest':
        """Reject settings unsupported by the current Harness contract."""

        if self.config:
            raise ValueError(f'{self.kind} harness config must be empty.')
        return self


class HarnessResponse(ResponseSchema):
    """One persisted local execution mechanism."""

    kind: Literal['louie', 'codex_cli', 'copilot_cli']
    version: Literal['v1']
    config: dict[str, object]
