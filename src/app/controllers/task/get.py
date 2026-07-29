"""Controller for describing a single-task execution."""

from src.app.schemas.task import GetResponse

from . import utils


async def get_task(run_id: str) -> GetResponse:
    """Return latest checkpoint state for one run identifier."""
    state = utils.TASK_RUNS.get(run_id)
    if state is None:
        return GetResponse(
            ok=False,
            run_id=run_id,
            iteration=0,
            status="failed",
            next_action="none",
            continuation_token=None,
            token_revision=0,
            error_code="run_not_found",
            message="Run was not found.",
            recoverable=False,
        )
    return GetResponse(**utils.checkpoint_payload(state))
