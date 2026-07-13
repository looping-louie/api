from fastapi import APIRouter, Query, Response, status
from src.app.schemas import (
    GetTaskResponse,
    RunMeetingRequest,
    RunMeetingResponse,
    TaskContinueRequest,
    TaskContinueResponse,
    TaskStartRequest,
    TaskStartResponse,
)
<<<<<<< HEAD
from src.app.controllers.meeting import run_meeting
from src.app.controllers.task import continue_task, get_task, start_task

from src.app.schemas.providers import (
    ProviderEnabledRequest,
    ProviderResponse,
    ProviderSetRequest,
    ProviderTestResponse
)

from src.app.controllers.providers import (
    list_providers,
    set_provider,
    set_provider_enabled,
    test_provider,
    unset_provider,
)
from src.app.controllers.skills import (
    create_skill,
    delete_skill,
    get_skill,
    list_skills,
    restore_skill,
    update_skill,
)
from src.app.schemas.skills import (
    SkillCreateRequest,
    SkillResponse,
    SkillSummaryResponse,
    SkillUpdateRequest,
)
=======
from src.app.controllers.harness_runner import run_harness
from src.app.controllers.task_runner import run_tasks
from src.app.controllers.meeting_runner import run_meeting
>>>>>>> 5065053 (ref(routers): se independizan últimas rutas)

from .api_v1 import router as api_v1_router

__all__ = [
    "api_v1_router",
]

# Create the router instance
router = APIRouter()


@router.post("/meeting/run", response_model=RunMeetingResponse)
async def meeting_run_endpoint(
    req: RunMeetingRequest,
) -> RunMeetingResponse:
    """
    Execute one structured multi-persona meeting.

    Participants contribute proposals, challengers identify blocking issues,
    and the loop iterates until approval or the maximum number of rounds is
    reached.

    Returns the final generated artifact together with the complete meeting
    trace and execution metrics.
    """
    return await run_meeting(req)
<<<<<<< HEAD


@router.post('/task/start', response_model=TaskStartResponse)
async def task_start_endpoint(req: TaskStartRequest) -> TaskStartResponse:
    """Start checkpoint-based task execution and return first action."""
    return await start_task(req)


@router.post('/task/continue', response_model=TaskContinueResponse)
async def task_continue_endpoint(req: TaskContinueRequest) -> TaskContinueResponse:
    """Advance one checkpoint transition for an existing task run."""
    return await continue_task(req)


@router.get('/task/{run_id}', response_model=GetTaskResponse)
async def task_get_endpoint(run_id: str) -> GetTaskResponse:
    """Return latest checkpoint state for one task run identifier."""
    return await get_task(run_id)
@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers_endpoint() -> list[ProviderResponse]:
    """Return all model providers and their current configuration state."""
    return await list_providers()


@router.put("/providers/{provider}", response_model=ProviderResponse)
async def set_provider_endpoint(
    provider: str,
    request: ProviderSetRequest,
) -> ProviderResponse:
    """Create or replace the configuration for a model provider."""
    return await set_provider(provider=provider, request=request)


@router.patch("/providers/{provider}/enabled", response_model=ProviderResponse)
async def set_provider_enabled_endpoint(
    provider: str,
    request: ProviderEnabledRequest,
) -> ProviderResponse:
    """Enable or disable a configured model provider."""
    return await set_provider_enabled(provider=provider, request=request)


@router.delete("/providers/{provider}/credential", status_code=status.HTTP_204_NO_CONTENT)
async def unset_provider_endpoint(provider: str) -> Response:
    """Delete the stored credential for a model provider."""
    await unset_provider(provider=provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/providers/{provider}/test", response_model=ProviderTestResponse)
async def test_provider_endpoint(provider: str) -> ProviderTestResponse:
    """Test the stored configuration by connecting to the provider."""
    return await test_provider(provider=provider)


@router.get(
    "/skills",
    response_model=list[SkillSummaryResponse],
)
async def list_skills_endpoint(
    include_deleted: bool = Query(default=False),
) -> list[SkillSummaryResponse]:
    """Return built-in, overridden and custom skills."""

    return await list_skills(
        include_deleted=include_deleted
    )


@router.get(
    "/skills/{skill_id}",
    response_model=SkillResponse,
)
async def get_skill_endpoint(skill_id: str) -> SkillResponse:
    """Return one active skill by id."""

    return await get_skill(skill_id=skill_id)


@router.post(
    "/skills",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_skill_endpoint(
    request: SkillCreateRequest,
) -> SkillResponse:
    """Create an organisation-owned custom skill."""

    return await create_skill(request=request)


@router.put(
    "/skills/{skill_id}",
    response_model=SkillResponse,
)
async def update_skill_endpoint(
    skill_id: str,
    request: SkillUpdateRequest,
) -> SkillResponse:
    """Edit a custom skill or override a built-in skill."""

    return await update_skill(
        skill_id=skill_id,
        request=request,
    )


@router.delete(
    "/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_skill_endpoint(skill_id: str) -> Response:
    """Hide a built-in skill or soft-delete a custom skill."""

    await delete_skill(skill_id=skill_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/skills/{skill_id}/restore",
    response_model=SkillResponse,
)
async def restore_skill_endpoint(skill_id: str) -> SkillResponse:
    """Restore a custom skill or revert to the built-in version."""

    return await restore_skill(skill_id=skill_id)
=======
>>>>>>> 5065053 (ref(routers): se independizan últimas rutas)
