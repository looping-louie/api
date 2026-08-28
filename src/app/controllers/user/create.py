"""Controller for registering the current User."""

from src.app.schemas.user import UserResponse
from src.app.services.users import UserService

from .response import user_response


class UserCreateController:
    """Register the request identity when it is new."""

    async def register_current(self, *, user_id: str) -> UserResponse:
        """Ensure that the request identity has a durable profile."""

        return user_response(await self._user_service.register(user_id=user_id))

    _user_service: UserService