import enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base for every application error. One-to-one with docs/04-api.md's error contract."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationAppError(AppError):
    code = "validation_error"
    status_code = 400


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = 401


class ForbiddenError(AppError):
    code = "forbidden"
    status_code = 403


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404


class ConflictError(AppError):
    code = "conflict"
    status_code = 409


class SemanticError(AppError):
    """Syntactically valid request that violates a business rule."""

    code = "semantic_error"
    status_code = 422


class RateLimitedError(AppError):
    code = "rate_limited"
    status_code = 429

    def __init__(
        self, message: str, *, retry_after: int, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message, details=details)
        self.retry_after = retry_after


class ImportErrorCode(enum.StrEnum):
    """The failure taxonomy from docs/03-import-pipeline.md.

    Closed set on purpose: every code owes the user distinct Dutch copy and an exit. A generic
    error makes the app feel broken, which is why there is no catch-all member here.
    """

    unsupported_url = "unsupported_url"
    private_or_removed = "private_or_removed"
    no_recipe_found = "no_recipe_found"
    low_confidence = "low_confidence"
    no_transcript = "no_transcript"
    silent_video = "silent_video"
    scraper_failed = "scraper_failed"
    model_failed = "model_failed"
    quota_exceeded = "quota_exceeded"
    media_too_large = "media_too_large"
    timeout = "timeout"


class ImportFailedError(AppError):
    """An import that could not produce a draft.

    Carries a taxonomy code rather than being one class per failure, because the set is fixed and
    the client switches on the code to choose copy and an exit route.
    """

    status_code = 422

    def __init__(
        self,
        error_code: ImportErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.code = str(error_code)
        self.error_code = error_code


def _error_body(code: str, message: str, details: dict[str, Any] | None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    response = JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )
    if isinstance(exc, RateLimitedError):
        response.headers["Retry-After"] = str(exc.retry_after)
    return response


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(
        status_code=400,
        content=_error_body("validation_error", "Ongeldige aanvraag.", {"errors": exc.errors()}),
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body("http_error", str(exc.detail), None),
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_error_body("internal_error", "Er ging iets mis. Probeer het opnieuw.", None),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
