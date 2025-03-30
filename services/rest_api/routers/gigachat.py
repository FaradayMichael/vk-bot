from typing import Any

from fastapi import APIRouter, Depends, Body
from gigachat.models import MessagesRole
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from schemas.base import SuccessResponse
from services.utils.client import UtilsClient
from utils.fastapi.depends.session import (
    get as ges_session
)
from utils.fastapi.depends.utils_clinet import (
    get as get_utils_client
)

from utils.fastapi.session import Session

router = APIRouter(
    prefix='/gigachat',
    tags=['gigachat']
)


class FunctionCall(BaseModel):
    name: str
    arguments: dict[Any, Any] | None = None


class Message(BaseModel):
    role: MessagesRole
    content: str = ""
    function_call: FunctionCall | None = None
    name: str | None = None
    attachments: list[str] | None = None
    data_for_context: list["Message"] | None = None
    id_: Any | None = Field(alias="id", default=None)


@router.post('/chat', response_model=str)
async def api_gigachat_chat(
        text: str = Body(media_type="text/plain", min_length=1, max_length=100),
        session: Session = Depends(ges_session),
        utils_client: UtilsClient = Depends(get_utils_client),
) -> str | JSONResponse:
    user = str(session.user.id)
    response = await utils_client.gpt_chat(user, text)
    return response.message

# TODO
# @router.post('/clear', response_model=SuccessResponse)
# async def api_gigachat_clear(
#         session: Session = Depends(ges_session),
#         utils_client: UtilsClient = Depends(get_utils_client),
# ) -> SuccessResponse | JSONResponse:
#     user = str(session.user.id)
#     await utils_client.gpt_clear(user)
#     return SuccessResponse()
