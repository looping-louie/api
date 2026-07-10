"""Thin controller delegating harness execution to the service layer."""

from src.app.schemas import RunHarnessRequest, RunHarnessResponse
from src.app.services.harness import run_harness as run_harness_service


async def run_harness(req: RunHarnessRequest) -> RunHarnessResponse:
    """Execute one harness run through the harness orchestration service."""
    return await run_harness_service(req)
