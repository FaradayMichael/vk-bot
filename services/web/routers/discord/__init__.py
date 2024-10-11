from fastapi import APIRouter

from . import (
    activities,
    messages
)

router = APIRouter(
    prefix='/discord'
)
router.include_router(
    activities.router,
    dependencies=None
)
router.include_router(
    messages.router
)
