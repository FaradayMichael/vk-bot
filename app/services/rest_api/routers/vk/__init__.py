from fastapi import APIRouter, Depends

from . import (
    messages
)
from app.services.rest_api.depends.auth import (
    check_auth,
    check_is_admin
)

router = APIRouter(prefix='/vk', tags=['vk'])
router.include_router(
    messages.admin_router,
    dependencies=[Depends(check_auth), Depends(check_is_admin)]
)
router.include_router(
    messages.router
)
