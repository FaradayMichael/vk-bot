from fastapi import APIRouter

from . import (
    activities
)

router = APIRouter(
    prefix='/steam'
)
router.include_router(
    activities.router
)
