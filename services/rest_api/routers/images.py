from fastapi import APIRouter
from starlette.responses import JSONResponse

from business_logic.images import (
    parse_image_tags
)
from schemas.images import (
    ImageUrl,
    ImageTagsResponse
)

router = APIRouter(
    prefix='/images',
    tags=['images']
)


@router.post('/parse_tags', response_model=ImageTagsResponse)
async def api_parse_image_tags(
        data: ImageUrl
) -> ImageTagsResponse | JSONResponse:
    result = await parse_image_tags(
        str(data.url)
    )
    return ImageTagsResponse(
        data=result
    )
