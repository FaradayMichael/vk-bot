from fastapi import (
    APIRouter,
    Depends
)

from . import (
    index
)


def register_routers(app):
    router = APIRouter()

    router.include_router(
        index.router
    )

    app.include_router(router)
    return app
