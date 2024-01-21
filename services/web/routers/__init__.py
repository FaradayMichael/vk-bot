from fastapi import (
    APIRouter,
    Depends
)

from . import (
    index,
    auth,
    triggers_answers
)
from services.web.depends.auth import check_auth


def register_routers(app):
    router = APIRouter()

    router.include_router(
        index.router,
        dependencies=[Depends(check_auth)] if not app.debug else []
    )
    router.include_router(
        auth.router
    )
    router.include_router(
        triggers_answers.router,
        dependencies=[Depends(check_auth)] if not app.debug else []
    )

    app.include_router(router)
    return app
