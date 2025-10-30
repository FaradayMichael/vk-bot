from pydantic import BaseModel, AnyUrl

from app.schemas.base import SuccessResponse


class ImageUrl(BaseModel):
    url: AnyUrl


class ImageTags(BaseModel):
    tags: list[str] = []
    description: str | None = None
    text_on_image: str | None = None
    products_data: list[str] = []

    def text(self, sep: str = '\n', limit: int = None) -> str:
        str_lst = [f"TAGS: {self.tags_text}"]
        if self.description:
            str_lst.append(f"DESCRIPTION: {self.description}")
        if self.text_on_image:
            str_lst.append(f"TEXT: {self.text_on_image}")
        if self.products_data:
            str_lst.append(self.get_products_data_text(limit))
        return sep.join(str_lst)

    @property
    def tags_text(self) -> str:
        return ', '.join(self.tags)

    def get_products_data_text(self, limit: int = None) -> str:
        return '\n'.join(self.products_data)[:limit]


class ImageTagsResponse(SuccessResponse):
    data: ImageTags
