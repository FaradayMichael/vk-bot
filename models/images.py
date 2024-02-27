from pydantic import BaseModel, AnyUrl

from models.base import SuccessResponse


class ImageUrl(BaseModel):
    url: AnyUrl


class ImageTags(BaseModel):
    tags: list[str] = []
    description: str | None = None
    products_data: list[str] = []

    @property
    def tags_text(self) -> str:
        return ', '.join(self.tags)

    @property
    def products_data_text(self) -> str:
        return '\n'.join(self.products_data)


class ImageTagsResponse(SuccessResponse):
    data: ImageTags
