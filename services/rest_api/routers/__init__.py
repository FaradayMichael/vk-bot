from fastapi import (
    APIRouter,
    Depends,
    FastAPI
)

from . import (
    admin
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

    app.include_router(router)
    return app
