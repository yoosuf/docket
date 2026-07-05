"""Translates every kind of error — domain exceptions, request validation
failures, and generic HTTP errors — into one consistent JSON shape:

    {"error": {"code": "...", "message": "...", "request_id": "...", "fields": [...]}}

`fields` is only present for validation errors. Before this, a
validation failure (`RequestValidationError`, FastAPI/Pydantic's default)
and a domain failure (`AppError`) produced two different response
shapes, which is exactly the kind of inconsistency that makes API
clients write fragile, exception-shape-specific error handling.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError

logger = logging.getLogger("docket")


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    fields: list[dict[str, str]] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _respond(status_code: int, detail: ErrorDetail) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=ErrorEnvelope(error=detail).model_dump(exclude_none=True))


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.exception("Unhandled application error", exc_info=exc)
    return _respond(
        exc.status_code,
        ErrorDetail(code=exc.code, message=str(exc), request_id=_request_id(request)),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(part) for part in error["loc"] if part != "body"), "message": error["msg"]}
        for error in exc.errors()
    ]
    return _respond(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            request_id=_request_id(request),
            fields=fields,
        ),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _respond(
        exc.status_code,
        ErrorDetail(code="HTTP_ERROR", message=str(exc.detail), request_id=_request_id(request)),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
