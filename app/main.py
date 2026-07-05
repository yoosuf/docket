"""Application entry point / composition root for the ASGI app.

Modular monolith: each business module under `app/modules/` owns its
own router and is mounted here. Adding a new module later is one new
`include_router` call — nothing else in this file changes.
"""
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestIdMiddleware
from app.modules.documents.router import document_types_router, router as documents_router


def create_app() -> FastAPI:
    settings = get_settings()
    settings.ensure_directories()

    app = FastAPI(
        title=settings.project_name,
        version="1.0.0",
        description=(
            "Generates DOCX/PDF documents from versioned templates and dynamic JSON data."
        ),
    )

    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(documents_router, prefix=settings.api_v1_prefix)
    app.include_router(document_types_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    return app


app = create_app()
