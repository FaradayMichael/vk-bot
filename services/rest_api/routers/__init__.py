from fastapi import (
    APIRouter,
    Depends,
    FastAPI
)

from . import (
    admin,
    triggers_answers,
    vk,
    images
)
from services.rest_api.depends.auth import (
    check_auth,
    check_is_admin
)

API_PREFIX = "/api/v1"


def register_routers(app: FastAPI):
    router = APIRouter(prefix=API_PREFIX)

    router.include_router(
        admin.router,
        dependencies=[Depends(check_auth), Depends(check_is_admin)] if not app.debug else []
    )

    router.include_router(
        triggers_answers.router,
        dependencies=[Depends(check_auth)] if not app.debug else []
    )

    router.include_router(
        vk.router,
        dependencies=[Depends(check_auth)] if not app.debug else []
    )

    router.include_router(
        images.router
    )

    app.include_router(router)
    return app
