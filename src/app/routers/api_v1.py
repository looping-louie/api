"""Versioned REST router composition."""

from fastapi import APIRouter

from .activities import router as activities_router
from .catalog import router as catalog_router
from .pipelines import router as pipelines_router
from .personas import router as personas_router
from .skills import router as skills_router
from .models import router as models_router
from .linked_services import router as linked_services_router
from .workers import router as workers_router


router = APIRouter(
    prefix="/api/v1",
)

router.include_router(personas_router)
router.include_router(skills_router)
router.include_router(activities_router)
router.include_router(pipelines_router)
router.include_router(catalog_router)
router.include_router(models_router)
router.include_router(linked_services_router)
router.include_router(workers_router)
