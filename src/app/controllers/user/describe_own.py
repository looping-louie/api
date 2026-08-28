"""Controller for retrieving the current User."""

from src.app.schemas.user import UserResponse
from src.app.services.users import UserService

from .response import user_response


class UserDescribeOwnController:
    """Retrieve the durable profile for the request identity."""

    async def get_current(self, *, user_id: str) -> UserResponse:
        """Return the durable profile for the request identity."""

        return user_response(await self._user_service.get(user_id=user_id))

    _user_service: UserService