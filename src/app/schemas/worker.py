"""HTTP schemas for runtime worker registration."""

from datetime import datetime

from .shared import ResponseSchema


class WorkerResponse(ResponseSchema):
    """One workspace worker registration and its most recent heartbeat."""

    id: str
    registered_at: datetime
    last_heartbeat_at: datetime