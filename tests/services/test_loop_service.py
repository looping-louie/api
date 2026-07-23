import pytest

from src.app.services.loop_service import (
    LoopCreate,
    LoopModelBinding,
    LoopService,
    LoopUpdate,
    LoopValidationError,
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
) -> LoopService:
    return LoopService(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )


def seed_loop_references(
    repository: FakeReferenceRepository,
) -> None:
    repository.seed(
        workspace_id="workspace-1",
        resource_type="council",
        resource_id="council-1",
        value={
            "items": [
                {
                    "role": "generator",
                    "persona_id": "persona-generator",
                    "skill_ids": ["skill-generator"],
                },
                {
                    "role": "reviewer",
                    "persona_id": "persona-reviewer",
                    "skill_ids": ["skill-reviewer"],
                },
            ],
        },
    )
    repository.seed(
        workspace_id="workspace-1",
        resource_type="persona",
        resource_id="persona-generator",
        value={"id": "persona-generator"},
    )
    repository.seed(
        workspace_id="workspace-1",
        resource_type="persona",
        resource_id="persona-reviewer",
        value={"id": "persona-reviewer"},
    )
    repository.seed(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_id="skill-generator",
        value={"id": "skill-generator"},
    )
    repository.seed(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_id="skill-reviewer",
        value={"id": "skill-reviewer"},
    )
    repository.seed(
        workspace_id="workspace-1",
        resource_type="model",
        resource_id="model-generator",
        value={"id": "model-generator"},
    )
    repository.seed(
        workspace_id="workspace-1",
        resource_type="model",
        resource_id="model-reviewer",
        value={"id": "model-reviewer"},
    )


@pytest.mark.asyncio
async def test_create_loop(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_loop_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    created = await service.create(
        user_id="user-1",
        payload=LoopCreate(
            name="Production Loop",
            description="Production review",
            council_id="council-1",
            max_iterations=4,
            model_bindings=[
                LoopModelBinding(
                    role="generator",
                    model_id="model-generator",
                ),
                LoopModelBinding(
                    role="reviewer",
                    model_id="model-reviewer",
                ),
            ],
        ),
    )

    assert created.workspace_id == "workspace-1"
    assert created.council_id == "council-1"
    assert created.max_iterations == 4
    assert len(created.model_bindings) == 2


@pytest.mark.asyncio
async def test_create_loop_rejects_missing_model(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_loop_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    with pytest.raises(ResourceNotFoundError):
        await service.create(
            user_id="user-1",
            payload=LoopCreate(
                name="Loop",
                description="Description",
                council_id="council-1",
                max_iterations=3,
                model_bindings=[
                    LoopModelBinding(
                        role="generator",
                        model_id="model-generator",
                    ),
                    LoopModelBinding(
                        role="reviewer",
                        model_id="missing-model",
                    ),
                ],
            ),
        )


@pytest.mark.asyncio
async def test_loop_new_use_rejects_retired_council_instruction(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_loop_references(reference_repository)
    reference_repository.set_historical_only(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_id="skill-reviewer",
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
            payload=LoopCreate(
                name="Loop",
                description="Description",
                council_id="council-1",
                max_iterations=3,
                model_bindings=[
                    LoopModelBinding(
                        role="generator",
                        model_id="model-generator",
                    ),
                    LoopModelBinding(
                        role="reviewer",
                        model_id="model-reviewer",
                    ),
                ],
            ),
        )


@pytest.mark.asyncio
async def test_create_loop_rejects_missing_role_binding(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_loop_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    with pytest.raises(LoopValidationError) as error:
        await service.create(
            user_id="user-1",
            payload=LoopCreate(
                name="Loop",
                description="Description",
                council_id="council-1",
                max_iterations=3,
                model_bindings=[
                    LoopModelBinding(
                        role="generator",
                        model_id="model-generator",
                    ),
                ],
            ),
        )

    assert "reviewer" in str(error.value)


@pytest.mark.asyncio
async def test_create_loop_rejects_unused_role_binding(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_loop_references(reference_repository)
    reference_repository.seed(
        workspace_id="workspace-1",
        resource_type="model",
        resource_id="model-challenger",
        value={"id": "model-challenger"},
    )
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    with pytest.raises(LoopValidationError) as error:
        await service.create(
            user_id="user-1",
            payload=LoopCreate(
                name="Loop",
                description="Description",
                council_id="council-1",
                max_iterations=3,
                model_bindings=[
                    LoopModelBinding(
                        role="generator",
                        model_id="model-generator",
                    ),
                    LoopModelBinding(
                        role="reviewer",
                        model_id="model-reviewer",
                    ),
                    LoopModelBinding(
                        role="challenger",
                        model_id="model-challenger",
                    ),
                ],
            ),
        )

    assert "challenger" in str(error.value)


@pytest.mark.asyncio
async def test_update_loop_iterations_preserves_configuration(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_loop_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    created = await service.create(
        user_id="user-1",
        payload=LoopCreate(
            name="Loop",
            description="Description",
            council_id="council-1",
            max_iterations=3,
            model_bindings=[
                LoopModelBinding(
                    role="generator",
                    model_id="model-generator",
                ),
                LoopModelBinding(
                    role="reviewer",
                    model_id="model-reviewer",
                ),
            ],
        ),
    )

    updated = await service.update(
        user_id="user-1",
        loop_id=created.id,
        payload=LoopUpdate(
            expected_version=1,
            max_iterations=6,
        ),
    )

    assert updated.max_iterations == 6
    assert updated.council_id == created.council_id
    assert updated.model_bindings == created.model_bindings
    assert updated.version == 2


@pytest.mark.asyncio
async def test_validate_detects_reference_removed_after_creation(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_loop_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )

    created = await service.create(
        user_id="user-1",
        payload=LoopCreate(
            name="Loop",
            description="Description",
            council_id="council-1",
            max_iterations=3,
            model_bindings=[
                LoopModelBinding(
                    role="generator",
                    model_id="model-generator",
                ),
                LoopModelBinding(
                    role="reviewer",
                    model_id="model-reviewer",
                ),
            ],
        ),
    )

    reference_repository.remove(
        workspace_id="workspace-1",
        resource_type="model",
        resource_id="model-reviewer",
    )

    with pytest.raises(ResourceNotFoundError):
        await service.validate(
            user_id="user-1",
            loop_id=created.id,
        )


@pytest.mark.asyncio
async def test_validate_existing_loop_allows_retired_instruction(
    tenant_service: TenantService,
    validation_service: ValidationService,
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
    composition_service: CompositionService,
) -> None:
    seed_loop_references(reference_repository)
    service = build_service(
        tenant_service=tenant_service,
        validation_service=validation_service,
        reference_resolver=reference_resolver,
        composition_service=composition_service,
    )
    created = await service.create(
        user_id="user-1",
        payload=LoopCreate(
            name="Loop",
            description="Description",
            council_id="council-1",
            max_iterations=3,
            model_bindings=[
                LoopModelBinding(
                    role="generator",
                    model_id="model-generator",
                ),
                LoopModelBinding(
                    role="reviewer",
                    model_id="model-reviewer",
                ),
            ],
        ),
    )
    reference_repository.set_historical_only(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_id="skill-reviewer",
    )

    with pytest.raises(ResourceNotFoundError):
        await service.update(
            user_id="user-1",
            loop_id=created.id,
            payload=LoopUpdate(
                expected_version=1,
                max_iterations=4,
            ),
        )

    validated = await service.validate(
        user_id="user-1",
        loop_id=created.id,
    )

    assert validated.id == created.id
