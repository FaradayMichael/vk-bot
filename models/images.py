from pydantic import BaseModel, AnyUrl

from models.base import SuccessResponse


class ImageUrl(BaseModel):
    url: AnyUrl


class ImageTags(BaseModel):
    tags: list[str] = []
    description: str | None = None


class ImageTagsResponse(SuccessResponse):
    data: ImageTags
