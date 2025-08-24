from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.business_logic.images import (
    parse_image_tags
)
from app.schemas.images import (
    ImageUrl,
    ImageTagsResponse
)
from app.services.rest_api.depends.rpc import (
    get_utils
)
from app.services.utils.client import UtilsClient

router = APIRouter(
    prefix='/images',
    tags=['images']
)


@router.post('/parse_tags', response_model=ImageTagsResponse)
async def api_parse_image_tags(
        data: ImageUrl,
        utils_client: UtilsClient = Depends(get_utils)
) -> ImageTagsResponse | JSONResponse:
    result = await utils_client.get_image_tags(str(data.url))
    return ImageTagsResponse(
        data=result
    )
