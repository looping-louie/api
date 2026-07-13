import pytest

from src.app.services.council_service import (
    CouncilAssignment,
    CouncilCreate,
    CouncilService,
    CouncilUpdate,
    CouncilValidationError,
)
from src.app.services.shared.composition_service import CompositionService
from src.app.services.shared.reference_resolver import (
    ReferenceResolver,
    ResourceNotFoundError,
)
from src.app.services.shared.tenant_service import TenantService
from src.app.services.shared.validation_service import ValidationService
from tests.fakes.reference_repository import FakeReferenceRepository


def build_service(
    *,
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    composition_service: CompositionService,
) -> CouncilService:
    return CouncilService(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )


def seed_council_references(
    repository: FakeReferenceRepository,
) -> None:
    repository.seed(
        workspace_id="workspace-1",
        resource_type="persona",
        resource_id="persona-1",
        value={"id": "persona-1"},
    )
    repository.seed(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_id="skill-1",
        value={"id": "skill-1"},
    )
    repository.seed(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_id="skill-2",
        value={"id": "skill-2"},
    )


@pytest.mark.asyncio
async def test_create_council(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_council_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    created = await service.create(
        user_id="user-1",
        payload=CouncilCreate(
            name="Engineering Council",
            description="Reviews implementation",
            assignments=[
                CouncilAssignment(
                    role=" Reviewer ",
                    persona_id="persona-1",
                    skill_ids=["skill-1", "skill-2"],
                ),
            ],
        ),
    )

    assert created.workspace_id == "workspace-1"
    assert created.assignments == (
        CouncilAssignment(
            role="reviewer",
            persona_id="persona-1",
            skill_ids=("skill-1", "skill-2"),
        ),
    )


@pytest.mark.asyncio
async def test_create_council_rejects_missing_reference(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    reference_repository.seed(
        workspace_id="workspace-1",
        resource_type="persona",
        resource_id="persona-1",
        value={"id": "persona-1"},
    )
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    with pytest.raises(ResourceNotFoundError):
        await service.create(
            user_id="user-1",
            payload=CouncilCreate(
                name="Council",
                description="Description",
                assignments=[
                    CouncilAssignment(
                        role="reviewer",
                        persona_id="persona-1",
                        skill_ids=["missing-skill"],
                    ),
                ],
            ),
        )


@pytest.mark.asyncio
async def test_create_council_rejects_duplicate_assignment(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_council_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    with pytest.raises(Exception) as error:
        await service.create(
            user_id="user-1",
            payload=CouncilCreate(
                name="Council",
                description="Description",
                assignments=[
                    CouncilAssignment(
                        role="reviewer",
                        persona_id="persona-1",
                        skill_ids=["skill-1"],
                    ),
                    CouncilAssignment(
                        role="REVIEWER",
                        persona_id="persona-1",
                        skill_ids=["skill-2"],
                    ),
                ],
            ),
        )

    assert "duplicate" in str(error.value).casefold()


@pytest.mark.asyncio
async def test_create_council_requires_skills(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_council_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    with pytest.raises(CouncilValidationError):
        await service.create(
            user_id="user-1",
            payload=CouncilCreate(
                name="Council",
                description="Description",
                assignments=[
                    CouncilAssignment(
                        role="reviewer",
                        persona_id="persona-1",
                        skill_ids=[],
                    ),
                ],
            ),
        )


@pytest.mark.asyncio
async def test_update_council_preserves_assignments(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_council_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    created = await service.create(
        user_id="user-1",
        payload=CouncilCreate(
            name="Council",
            description="Initial",
            assignments=[
                CouncilAssignment(
                    role="reviewer",
                    persona_id="persona-1",
                    skill_ids=["skill-1"],
                ),
            ],
        ),
    )

    updated = await service.update(
        user_id="user-1",
        council_id=created.id,
        payload=CouncilUpdate(
            expected_version=1,
            description="Updated",
        ),
    )

    assert updated.description == "Updated"
    assert updated.assignments == created.assignments
    assert updated.version == 2
