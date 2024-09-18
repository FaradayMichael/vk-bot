import logging
from enum import StrEnum
from types import NoneType
from typing import (
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
    data: Any | None = None


class ListData(BaseModel):
    total: int
    limit: int
    page: int
    items: list[Any]


class ErrorResponse(BaseModel):
    success: bool = False
    error: str | dict | NoneType = None
    validation_error: list[ValidationError] | None = None
    debug: str | None = None


class UpdateErrorResponse(BaseModel):
    success: bool = False
    errors: list[Any]


class Range(BaseModel):
    from_: int
    to: int | None = None


class BaseSearchQueryParams(BaseModel):
    q: str | None = Field(default="", description="search query")


class BaseLangSearchQueryParams(BaseSearchQueryParams):
    lang: LangsEnum = Field(default=LangsEnum.EN.value, description='Search lang')


class BaseListQueryParams(BaseModel):
    limit: int = Field(LIMIT_PER_PAGE, gt=0)
    page: int = Field(1, gt=0)


def round_decimal(
        value: Decimal | None,
        template: Decimal = Decimal('1.00'),
        round_str: str = ROUND_HALF_UP
) -> Decimal | None:
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
