"""Cross-cutting request middleware."""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

REQUEST_ID_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a correlation id to every request.

    Reuses a caller-supplied `X-Request-Id` if present (so a request can
    be traced end-to-end across an upstream gateway), otherwise mints
    one. Available to route handlers/exception handlers via
    `request.state.request_id`, and echoed back on every response —
    success or error — so a client's error report can be matched to a
    server log line.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
