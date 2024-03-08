from typing import (
    Any,
    Optional
)

from fastapi import (
    Request,
    FastAPI
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import (
    JSONResponse,
    RedirectResponse
)
from pydantic_core import (
    ValidationError as CoreValidationError
)
from starlette.exceptions import (
    HTTPException as StarletteHTTPException
)

from models.base import (
    ValidationError,
    ErrorResponse,
    UpdateErrorResponse
)

TRANSLATIONS_BY_STATUS = {
    400: {
        "value_en": "Validation error",
        "value_ru": "Ошибка валидации",
        "value_es": "Error de validacion",
        "value_cn": "验证错误"
    },
    401: {
        "value_en": "Unauthorized",
        "value_ru": "Не авторизован",
        "value_es": "No autorizado",
        "value_cn": "未经授权"
    },
    403: {
        "value_en": "Forbidden",
        "value_ru": "Доступ запрещен",
        "value_es": "Acceso denegado",
        "value_cn": "访问被拒绝"
    },
    404: {
        "value_en": "Not found",
        "value_ru": "Не найдено",
        "value_es": "Extraviado",
        "value_cn": "未找到"
    },
    500: {
        "value_en": "Internal Server Error",
        "value_ru": "Внутренняя ошибка сервера",
        "value_es": "Error Interno del Servidor",
        "value_cn": "内部服务器错误"
    }
}


class UnauthenticatedException(Exception):
    pass


class UnauthenticatedExceptionWeb(Exception):
    pass


class CustomValidationException(Exception):
    ...


class ForbiddenException(Exception):
    pass


class UpdateExpiredException(Exception):
    pass


async def error_409(errors: list[Any]):
    return JSONResponse(
        status_code=409,
        content=UpdateErrorResponse(errors=errors).model_dump_json()
    )


async def ok_204() -> JSONResponse:
    return JSONResponse(
        status_code=204,
        content=None
    )


async def error_500(detail: Optional[str] = None, debug: Optional[str] = None) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=detail or TRANSLATIONS_BY_STATUS.get(500),
            debug=debug
        ).model_dump())


async def error_400_with_detail(detail: Optional[str] = None, debug: Optional[str] = None) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=detail or TRANSLATIONS_BY_STATUS.get(400),
            debug=debug).model_dump()
    )


async def error_404(message: Optional[str] = None) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error=message or TRANSLATIONS_BY_STATUS.get(404)
        ).model_dump()
    )


async def error_401(message: Optional[str] = None) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=ErrorResponse(
            error=message or TRANSLATIONS_BY_STATUS.get(401)
        ).model_dump()
    )


async def error_403(message: Optional[str] = None) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=ErrorResponse(
            error=message or TRANSLATIONS_BY_STATUS.get(403)
        ).model_dump()
    )


async def error_400(message: Optional[str | dict] = None) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=message or TRANSLATIONS_BY_STATUS.get(400)
        ).model_dump()
    )


async def error_400_with_content(content: dict) -> JSONResponse:
    return JSONResponse(status_code=400, content=content)


def register_exception_handler(app: FastAPI):
    if not app.state.config.debug:
        @app.exception_handler(Exception)
        async def http_exception_handler(request, exc) -> JSONResponse:
            return await error_500(debug=str(exc) if app.state.config.debug else None)

        @app.exception_handler(StarletteHTTPException)
        async def starlette_http_exception_handler(request, exc) -> JSONResponse:
            return await error_500(debug=str(exc) if app.state.config.debug else None)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(CoreValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        validation_error = None
        errors = exc.errors()
        if errors:
            validation_error = []
            for i in errors:
                validation_error.append(
                    ValidationError(
                        field='.'.join([str(l_) for l_ in i['loc'][1:]]),
                        message=i['msg']
                    )
                )

        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=TRANSLATIONS_BY_STATUS.get(400),
                validation_error=validation_error,
                debug=str(exc) if app.state.config.debug else None
            ).model_dump()
        )

    @app.exception_handler(UnauthenticatedException)
    async def unauthenticated_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return await error_401()

    @app.exception_handler(UnauthenticatedExceptionWeb)
    async def unauthenticated_exception_handler(request: Request, exc: RequestValidationError) -> RedirectResponse:
        return RedirectResponse('/auth/login', status_code=302)

    @app.exception_handler(ForbiddenException)
    async def forbidden_exception_handler(request: Request, exc: ForbiddenException) -> JSONResponse:
        return await error_403()

    @app.exception_handler(UpdateExpiredException)
    async def update_fobidden_exception_handler(request: Request, exc: UpdateExpiredException) -> JSONResponse:
        return await error_400(",".join(exc.args))

    @app.exception_handler(CustomValidationException)
    async def validation_error_handler(request: Request, exc: CustomValidationException) -> JSONResponse:
        return await error_400(", ".join(exc.args))
