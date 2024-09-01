import logging
from enum import StrEnum
from types import NoneType
from typing import (
    Optional,
    List,
    Any
)

from decimal import (
    Decimal,
    ROUND_HALF_UP
)
from pydantic import BaseModel, Field

from misc.consts import (
    LIMIT_PER_PAGE,
    LangsEnum
)


class ValidationError(BaseModel):
    field: str
    message: str


class SuccessResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None


class ListData(BaseModel):
    total: int
    limit: int
    page: int
    items: List[Any]


class ErrorResponse(BaseModel):
    success: bool = False
    error: str | dict | NoneType = None
    validation_error: Optional[List[ValidationError]] = None
    debug: Optional[str] = None


class UpdateErrorResponse(BaseModel):
    success: bool = False
    errors: List[Any]


class Range(BaseModel):
    from_: int
    to: Optional[int] = None


class BaseSearchQueryParams(BaseModel):
    q: Optional[str] = Field(default="", description="search query")


class BaseLangSearchQueryParams(BaseSearchQueryParams):
    lang: LangsEnum = Field(default=LangsEnum.EN.value, description='Search lang')


class BaseListQueryParams(BaseModel):
    limit: int = Field(LIMIT_PER_PAGE, gt=0)
    page: int = Field(1, gt=0)


def round_decimal(
        value: Optional[Decimal],
        template: Decimal = Decimal('1.00'),
        round_str: str = ROUND_HALF_UP
) -> Optional[Decimal]:
    if value is None:
        return None
    return value.quantize(template, rounding=round_str)


class AttachmentType(StrEnum):
    PHOTO = "photo"
    DOC = "doc"
    VIDEO = "video"

    @staticmethod
    def by_content_type(
            content_type: str
    ) -> "AttachmentType":
        match content_type:
            case 'image/png':
                return AttachmentType.PHOTO
            case "image/jpeg":
                return AttachmentType.PHOTO
            case "image/bmp":
                return AttachmentType.PHOTO
            case "video/mp4":
                return AttachmentType.VIDEO
            case "video/quicktime":
                return AttachmentType.VIDEO
            case "video/webm":
                return AttachmentType.VIDEO
            case _ as arg:
                logging.info(f"{arg=}")
                return AttachmentType.DOC

    @staticmethod
    def by_ext(
            ext: str,
    ) -> "AttachmentType":
        match ext.lower():
            case 'jpg':
                return AttachmentType.PHOTO
            case 'jpeg':
                return AttachmentType.PHOTO
            case 'bmp':
                return AttachmentType.PHOTO
            case 'mp4':
                return AttachmentType.VIDEO
            case 'mov':
                return AttachmentType.VIDEO
            case 'mkv':
                return AttachmentType.VIDEO
            case 'avi':
                return AttachmentType.VIDEO
            case _ as arg:
                logging.info(f"{arg=}")
                return AttachmentType.DOC
