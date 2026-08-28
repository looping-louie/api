"""Controllers for current User HTTP operations."""

from src.app.services.models.catalog import ModelCatalogService
from src.app.services.users import UserService

from .create import UserCreateController
from .describe_own import UserDescribeOwnController
from .get_own_model import UserGetOwnModelController
from .list_own_models import UserListOwnModelsController
from .patch_own import UserPatchOwnController


class UserController(
    UserCreateController,
    UserDescribeOwnController,
    UserGetOwnModelController,
    UserListOwnModelsController,
    UserPatchOwnController,
):
    """Compose endpoint-specific current User controllers."""

    def __init__(
        self,
        *,
        service: UserService,
        model_catalog_service: ModelCatalogService,
    ) -> None:
        """Store services required by current User operations."""

        self._user_service = service
        self._model_catalog_service = model_catalog_service


__all__ = [
    'UserController',
    'UserCreateController',
    'UserDescribeOwnController',
    'UserGetOwnModelController',
    'UserListOwnModelsController',
    'UserPatchOwnController',
]
