from fastapi import APIRouter

from . import (
    activities,
    statuses,
)

router = APIRouter(prefix="/steam")
router.include_router(activities.router)
router.include_router(statuses.router)
