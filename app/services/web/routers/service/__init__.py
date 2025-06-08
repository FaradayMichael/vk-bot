from fastapi import APIRouter

from . import (
    triggers_answers,
    triggers_history
)

router = APIRouter(
    prefix='/service'
)
router.include_router(
    triggers_answers.router
)
router.include_router(
    triggers_history.router
)
