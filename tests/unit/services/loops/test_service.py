"""Unit tests for loop application behavior."""

from __future__ import annotations

from itertools import count

import pytest

from src.app.models.loop import LoopOutputContract, LoopStopConditions
from src.app.services.loops.service import LoopService
from src.app.services.loops.types import (
    ArchivedLoopImmutableError,
    LoopAgentInput,
    LoopCreate,
    LoopPatch,
    LoopValidationError,
)
from src.app.services.personas import PersonaLinkedServiceSelection
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant import TenantService
from tests.conftest import IncrementingClock
from tests.fakes.loop_repository import FakeLoopRepository
from tests.fakes.persona_linked_service_selection_repository import (
    FakePersonaLinkedServiceSelectionRepository,
)
from tests.fakes.loop_run_retention_repository import (
    FakeLoopRunRetentionRepository,
)
from tests.fakes.dependency_checker import FakeDependencyChecker
from tests.fakes.reference_repository import FakeReferenceRepository


def build_service(
    *,
    repository: FakeLoopRepository,
    tenant_service: TenantService,
    reference_resolver: ReferenceResolver,
    persona_linked_service_selection_repository: FakePersonaLinkedServiceSelectionRepository | None = None,
    dependency_checker: FakeDependencyChecker | None = None,
    loop_run_repository: FakeLoopRunRetentionRepository | None = None,
) -> LoopService:
    """Build a deterministic service and seed selectable references."""

    identifiers = count(1)
    return LoopService(
        repository=repository,
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
        persona_linked_service_selection_repository=(
            persona_linked_service_selection_repository
            or FakePersonaLinkedServiceSelectionRepository()
        ),
        dependency_checker=dependency_checker or FakeDependencyChecker(),
        loop_run_repository=(
            loop_run_repository or FakeLoopRunRetentionRepository()
        ),
        id_factory=lambda: f"id-{next(identifiers)}",
        clock=IncrementingClock(),
    )


def seed_references(repository: FakeReferenceRepository) -> None:
    """Seed every model and persona used by loop tests."""

    for resource_type, resource_ids in {
        "model": ("model-1", "model-2", "model-3"),
        "persona": ("persona-1", "persona-2", "persona-3"),
    }.items():
        for resource_id in resource_ids:
            repository.seed(
                workspace_id="workspace-1",
                resource_type=resource_type,
                resource_id=resource_id,
                value={"id": resource_id},
            )


def agent(
    position: int,
    role: str,
    *,
    agent_id: str | None = None,
) -> LoopAgentInput:
    """Build one agent input from a test position and role."""

    return LoopAgentInput(
        id=agent_id,
        model_id=f"model-{position}",
        persona_id=f"persona-{position}",
        role=role,
    )


def payload(
    *,
    flow: str = "direct",
    agents: tuple[LoopAgentInput, ...] | None = None,
    stop_conditions: LoopStopConditions | None = None,
    output_contract: LoopOutputContract | None = None,
) -> LoopCreate:
    """Build a valid loop create input with overridable aggregate fields."""

    return LoopCreate(
        title="Idea shaping",
        description="Shape one idea.",
        flow=flow,
        stop_conditions=stop_conditions or LoopStopConditions(
            max_iterations=3
        ),
        agents=(
            agents
            if agents is not None
            else (agent(1, "generator"),)
        ),
        output_contract=output_contract or LoopOutputContract(
            type="text",
            description="Human-readable answer.",
            files=(),
            schema=None,
        ),
    )


@pytest.fixture
def repository() -> FakeLoopRepository:
    """Return an empty loop repository."""

    return FakeLoopRepository()


@pytest.fixture
def service(
    repository: FakeLoopRepository,
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> LoopService:
    """Return a service with all common references available."""

    seed_references(reference_repository)
    return build_service(
        repository=repository,
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flow", "agents"),
    [
        ("direct", (agent(1, "generator"),)),
        (
            "refinement",
            (agent(1, "generator"), agent(2, "reviewer")),
        ),
        (
            "roundtable",
            (
                agent(1, "generator"),
                agent(2, "generator"),
                agent(3, "aggregator"),
            ),
        ),
    ],
)
async def test_create_supports_each_flow(
    service: LoopService,
    repository: FakeLoopRepository,
    flow: str,
    agents: tuple[LoopAgentInput, ...],
) -> None:
    """Each supported role combination creates an active audited loop."""

    created = await service.create(
        user_id="user-1",
        payload=payload(flow=flow, agents=agents),
    )

    assert created.flow == flow
    assert created.status == "active"
    assert all(created_agent.id for created_agent in created.agents)
    assert repository.entries[-1].change_type == "created"
    assert repository.entries[-1].actor_id == "user-1"
    assert repository.entries[-1].content["id"] == created.id


@pytest.mark.asyncio
async def test_create_allows_persona_selection_without_legacy_model(
    repository: FakeLoopRepository,
    tenant_service: TenantService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
) -> None:
    """A Persona linked-service selection makes a loop model ID unnecessary."""

    seed_references(reference_repository)
    selection_repository = FakePersonaLinkedServiceSelectionRepository()
    await selection_repository.replace_for_persona(
        persona_id='persona-1',
        selection=PersonaLinkedServiceSelection(
            linked_service_id='linked-service-1',
            model_id='model-1',
        ),
    )
    loop_service = build_service(
        repository=repository,
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
        persona_linked_service_selection_repository=selection_repository,
    )

    created = await loop_service.create(
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

    assert created.agents[0].model_id is None


@pytest.mark.asyncio
async def test_patch_replaces_agents_and_records_only_changed_field(
    service: LoopService,
    repository: FakeLoopRepository,
) -> None:
    """Agent replacement preserves omitted fields and writes a concise diff."""

    created = await service.create(
        user_id="user-1",
        payload=payload(),
    )
    replacement = (agent(2, "generator", agent_id="agent-explicit"),)

    updated = await service.patch(
        user_id="user-1",
        loop_id=created.id,
        payload=LoopPatch(
            provided_fields=frozenset({"agents"}),
            agents=replacement,
        ),
    )

    assert updated.title == created.title
    assert updated.agents[0].id == "agent-explicit"
    assert set(repository.entries[-1].diff) == {"agents"}
    assert repository.entries[-1].content is None


@pytest.mark.asyncio
async def test_status_transitions_include_archive_reactivation(
    service: LoopService,
    repository: FakeLoopRepository,
) -> None:
    """Disabled, archived, and reactivated transitions use specific events."""

    current = await service.create(user_id="user-1", payload=payload())
    expected = [
        ("disabled", "disabled"),
        ("active", "enabled"),
        ("archived", "archived"),
        ("active", "enabled"),
    ]
    for status, event in expected:
        current = await service.patch(
            user_id="user-1",
            loop_id=current.id,
            payload=LoopPatch(
                provided_fields=frozenset({"status"}),
                status=status,
            ),
        )
        assert current.status == status
        assert repository.entries[-1].change_type == event


@pytest.mark.asyncio
async def test_archived_loop_rejects_non_reactivation_change(
    service: LoopService,
) -> None:
    """An archived loop accepts only a status-only reactivation."""

    created = await service.create(user_id="user-1", payload=payload())
    await service.patch(
        user_id="user-1",
        loop_id=created.id,
        payload=LoopPatch(
            provided_fields=frozenset({"status"}),
            status="archived",
        ),
    )

    with pytest.raises(ArchivedLoopImmutableError):
        await service.patch(
            user_id="user-1",
            loop_id=created.id,
            payload=LoopPatch(
                provided_fields=frozenset({"title"}),
                title="Changed",
            ),
        )


@pytest.mark.asyncio
async def test_patch_rejects_no_effective_change(
    service: LoopService,
) -> None:
    """Supplying the current value does not create a changelog entry."""

    created = await service.create(user_id="user-1", payload=payload())

    with pytest.raises(LoopValidationError):
        await service.patch(
            user_id="user-1",
            loop_id=created.id,
            payload=LoopPatch(
                provided_fields=frozenset({"title"}),
                title=created.title,
            ),
        )


@pytest.mark.asyncio
async def test_delete_retains_final_snapshot(
    service: LoopService,
    repository: FakeLoopRepository,
) -> None:
    """Deletion removes the loop but leaves a final audited representation."""

    created = await service.create(user_id="user-1", payload=payload())
    await service.delete(user_id="user-1", loop_id=created.id)
    entries, total = await service.list_changelog(
        user_id="user-1",
        loop_id=created.id,
        offset=0,
    )

    assert await repository.get(
        workspace_id="workspace-1",
        loop_id=created.id,
    ) is None
    assert total == 2
    assert entries[0].change_type == "deleted"
    assert entries[0].content["id"] == created.id


@pytest.mark.asyncio
async def test_delete_archives_loop_with_retained_runs(
    repository: FakeLoopRepository,
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """Deletion archives a loop when its execution history must be retained."""

    run_repository = FakeLoopRunRetentionRepository()
    seed_references(reference_repository)
    service = build_service(
        repository=repository,
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
        loop_run_repository=run_repository,
    )
    created = await service.create(user_id="user-1", payload=payload())
    run_repository.loop_ids.add(("workspace-1", created.id))

    await service.delete(user_id="user-1", loop_id=created.id)

    retained = await repository.get(
        workspace_id="workspace-1",
        loop_id=created.id,
    )
    assert retained is not None
    assert retained.status == "archived"
    assert repository.entries[-1].change_type == "archived"
