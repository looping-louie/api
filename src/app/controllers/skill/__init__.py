"""Controllers for skill HTTP operations."""

from src.app.services.skill_service import SkillService

from .create import SkillCreateController
from .delete import SkillDeleteController
from .describe import SkillDescribeController
from .list import SkillListController
from .patch import SkillPatchController


class SkillController(
    SkillListController,
    SkillDescribeController,
    SkillCreateController,
    SkillPatchController,
    SkillDeleteController,
):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(self, *, skill_service: SkillService) -> None:
        """Store the shared skill application service."""
        self._skill_service = skill_service


__all__ = [
    "SkillController",
    "SkillCreateController",
    "SkillDeleteController",
    "SkillDescribeController",
    "SkillListController",
    "SkillPatchController",
]
