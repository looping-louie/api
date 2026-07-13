import pytest

from src.app.services.persona_service import PersonaService
from src.app.services.shared.instruction_service import (
    InstructionCreate,
    InstructionNotFoundError,
    InstructionService,
    InstructionUpdate,
)
from src.app.services.shared.tenant_service import (
    TenantService,
    WorkspaceMembership,
)
from tests.fakes.tenant_repository import FakeTenantRepository


def build_persona_service(
    instruction_service: InstructionService,
) -> PersonaService:
    repository = FakeTenantRepository(
        [
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-1",
                is_default=True,
            ),
        ]
    )

    return PersonaService(
        tenant_service=TenantService(repository=repository),
        instruction_service=instruction_service,
    )


@pytest.mark.asyncio
async def test_persona_crud_flow(
    instruction_service: InstructionService,
) -> None:
    service = build_persona_service(instruction_service)

    created = await service.create(
        user_id="user-1",
        payload=InstructionCreate(
            name="Tech Lead",
            description="Technical reviewer",
            instructions="Review architecture and implementation.",
        ),
    )

    assert created.instruction_type == "persona"
    assert created.workspace_id == "workspace-1"

    summaries = await service.list(user_id="user-1")

    assert len(summaries) == 1
    assert summaries[0].id == created.id

    described = await service.describe(
        user_id="user-1",
        persona_id=created.id,
    )

    assert described == created

    updated = await service.update(
        user_id="user-1",
        persona_id=created.id,
        payload=InstructionUpdate(
            expected_version=1,
            description="Senior technical reviewer",
        ),
    )

    assert updated.description == "Senior technical reviewer"
    assert updated.version == 2

    await service.delete(
        user_id="user-1",
        persona_id=created.id,
    )

    with pytest.raises(InstructionNotFoundError):
        await service.describe(
            user_id="user-1",
            persona_id=created.id,
        )
