from pydantic import BaseModel, AnyUrl

from models.base import SuccessResponse


class ImageUrl(BaseModel):
    url: AnyUrl


class ImageTags(BaseModel):
    tags: list[str] = []
    description: str | None = None
    products_data: list[str] = []

    def text(self, sep: str = '\n') -> str:
        str_lst = [f"tags: {self.tags_text}"]
        if self.description:
            str_lst.append(self.description)
        if self.products_data:
            str_lst.append(self.products_data_text)
        return sep.join(str_lst)

    @property
    def tags_text(self) -> str:
        return ', '.join(self.tags)

    @property
    def products_data_text(self) -> str:
        return '\n'.join(self.products_data)


class ImageTagsResponse(SuccessResponse):
    data: ImageTags
