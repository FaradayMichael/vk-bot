from fastapi import APIRouter, Depends

from . import activities, messages, statuses
from ...depends.auth import check_auth


def register_routes(parent: APIRouter, debug: bool = True) -> APIRouter:
    router = APIRouter(prefix="/discord")
    router.include_router(
        activities.router,
    )
    router.include_router(
        statuses.router,
    )
    router.include_router(
        messages.router, dependencies=[Depends(check_auth)] if not debug else []
    )

    parent.include_router(router)
    return parent
