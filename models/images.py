from pydantic import BaseModel, AnyUrl

from models.base import SuccessResponse


class ImageUrl(BaseModel):
    url: AnyUrl


class ImageTags(BaseModel):
    tags: list[str] = []
    description: str | None = None

    @property
    def tags_text(self) -> str:
        return ', '.join(self.tags)


class ImageTagsResponse(SuccessResponse):
    data: ImageTags
