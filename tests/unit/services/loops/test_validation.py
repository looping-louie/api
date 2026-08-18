"""Boundary tests for loop aggregate validation."""

from __future__ import annotations

import pytest

from src.app.models.loop import LoopOutputContract, LoopStopConditions
from src.app.services.loops.service import LoopService
from src.app.services.loops.types import (
    LoopAgentInput,
    LoopValidationError,
)
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant import TenantService
from tests.fakes.loop_repository import FakeLoopRepository
from tests.fakes.reference_repository import FakeReferenceRepository
from tests.unit.services.loops.test_service import (
    agent,
    build_service,
    payload,
    seed_references,
)


@pytest.fixture
def service(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> LoopService:
    """Return a loop service with common selectable references."""

    seed_references(reference_repository)
    return build_service(
        repository=FakeLoopRepository(),
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flow", "agents"),
    [
        ("direct", ()),
        (
            "direct",
            (agent(1, "aggregator"), agent(2, "aggregator")),
        ),
        (
            "direct",
            (agent(1, "generator"), agent(2, "generator")),
        ),
        (
            "direct",
            (agent(1, "generator"), agent(2, "reviewer")),
        ),
        ("refinement", (agent(1, "generator"),)),
        (
            "refinement",
            (agent(1, "generator"), agent(2, "generator")),
        ),
        (
            "refinement",
            (
                agent(1, "generator"),
                agent(2, "reviewer"),
                agent(3, "aggregator"),
            ),
        ),
        (
            "roundtable",
            (agent(1, "generator"), agent(2, "aggregator")),
        ),
        (
            "roundtable",
            (agent(1, "generator"), agent(2, "generator")),
        ),
        (
            "roundtable",
            (
                agent(1, "generator"),
                agent(2, "generator"),
                agent(3, "reviewer"),
                agent(4, "aggregator"),
            ),
        ),
    ],
)
async def test_create_rejects_invalid_flow_roles(
    service: LoopService,
    flow: str,
    agents: tuple[LoopAgentInput, ...],
) -> None:
    """Flow validation rejects every invalid cardinality boundary."""

    with pytest.raises(LoopValidationError):
        await service.create(
            user_id="user-1",
            payload=payload(flow=flow, agents=agents),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "conditions",
    [
        LoopStopConditions(),
        LoopStopConditions(max_tokens=0),
        LoopStopConditions(timeout_seconds=-1),
    ],
)
async def test_create_rejects_invalid_stop_conditions(
    service: LoopService,
    conditions: LoopStopConditions,
) -> None:
    """At least one positive stop condition is mandatory."""

    with pytest.raises(LoopValidationError):
        await service.create(
            user_id="user-1",
            payload=payload(stop_conditions=conditions),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "contract",
    [
        LoopOutputContract(
            type="files",
            description="Files.",
            files=(),
            schema=None,
        ),
        LoopOutputContract(
            type="json",
            description="JSON.",
            files=(),
            schema=None,
        ),
    ],
)
async def test_create_rejects_incomplete_output_contracts(
    service: LoopService,
    contract: LoopOutputContract,
) -> None:
    """Type-specific output data is required."""

    with pytest.raises(LoopValidationError):
        await service.create(
            user_id="user-1",
            payload=payload(output_contract=contract),
        )


@pytest.mark.asyncio
async def test_create_rejects_model_omission_without_persona_selection(
    service: LoopService,
) -> None:
    """An agent requires a legacy model unless its Persona selects one."""

    with pytest.raises(LoopValidationError, match='linked-service selection'):
        await service.create(
            user_id='user-1',
            payload=payload(
                agents=(
                    LoopAgentInput(
                        model_id=None,
                        persona_id='persona-1',
                        role='generator',
                    ),
                ),
            ),
        )
