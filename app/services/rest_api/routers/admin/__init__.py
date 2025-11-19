from fastapi import APIRouter

from . import users


router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(users.router)
