from fastapi import APIRouter

from .councils import router as councils_router
from .loops import router as loops_router
from .personas import router as personas_router
from .skills import router as skills_router
from .models import router as models_router
from .providers import router as providers_router


router = APIRouter(
    prefix="/api/v1",
)

router.include_router(personas_router)
router.include_router(skills_router)
router.include_router(councils_router)
router.include_router(loops_router)
router.include_router(models_router)
router.include_router(providers_router)
