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
    q: Optional[str] = Field(default=None, description="search query")


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
