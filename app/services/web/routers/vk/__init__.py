from fastapi import APIRouter

from . import messages

router = APIRouter(prefix="/vk")
router.include_router(messages.router)
