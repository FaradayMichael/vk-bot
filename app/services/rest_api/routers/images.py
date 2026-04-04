from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.schemas.images import ImageUrl, ImageTagsResponse
from app.services.rest_api.depends.rpc import get_utils
from app.services.utils.client import UtilsClient
from app.services.utils.models.asynctask import ImageDescriptionResponse

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/parse_tags", response_model=ImageTagsResponse)
async def api_parse_image_tags(
        data: ImageUrl,
        utils_client: UtilsClient = Depends(get_utils),
) -> ImageTagsResponse | JSONResponse:
    result = await utils_client.get_image_tags(str(data.url))
    return ImageTagsResponse(data=result)


@router.post("/image_description", response_model=ImageDescriptionResponse)
async def api_get_image_description(
        data: ImageUrl,
        utils_client: UtilsClient = Depends(get_utils),
) -> ImageDescriptionResponse | JSONResponse:
    return await utils_client.get_image_description(str(data.url))
