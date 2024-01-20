from fastapi import (
    APIRouter,
    Depends
)

from . import (
    index,
    auth
)


def register_routers(app):
    router = APIRouter()

    router.include_router(
        index.router
    )
    router.include_router(
        auth.router
    )

    app.include_router(router)
    return app
