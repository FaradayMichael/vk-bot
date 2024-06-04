from fastapi import APIRouter

from . import (
    activities
)

router = APIRouter(
    prefix='/discord'
)
router.include_router(
    activities.router
)
