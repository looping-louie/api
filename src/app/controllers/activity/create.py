"""Controller for creating activity definitions."""

from src.app.schemas.activity import ActivityCreateRequest, ActivityResponse
from src.app.models.pipeline import PipelineHarness
from src.app.services.activities.service import ActivityService


class ActivityCreateController:
    """Create one activity definition."""

    async def create(
        self,
        *,
        user_id: str,
        payload: ActivityCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> ActivityResponse:
        """Create one activity."""
        document = await self._activity_service.create(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            activity_type=payload.type,
            config=payload.config.model_dump(by_alias=True),
            model_id=payload.model_id,
            harness=(
                PipelineHarness(
                    kind=payload.harness.kind,
                    version=payload.harness.version,
                    config=payload.harness.config,
                )
                if payload.harness is not None
                else None
            ),
            requested_workspace_id=requested_workspace_id,
        )
        return ActivityResponse.model_validate(document)

    _activity_service: ActivityService
