"""FastAPI application factory.

Composition root: builds the app, attaches middleware, mounts routers
and registers exception handlers. Everything else lives in the api/
package or below.

The factory pattern (`create_app`) lets tests build an isolated app per
test session instead of importing a module-level singleton, which
avoids cross-test contamination of dependency overrides.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.exception_handlers import register_exception_handlers
from src.api.routers import alerts as alerts_router
from src.api.routers import files as files_router
from src.core.config import get_settings
from src.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(title="File exchange", version="0.2.0")

    # CORS allow-list comes from Settings so dev and prod can configure
    # origins via env without code changes. The original wildcard policy
    # combined with allow_credentials was unnecessarily permissive
    # (and warned about by Starlette).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.include_router(files_router.router)
    app.include_router(alerts_router.router)

    register_exception_handlers(app)

    return app


app = create_app()
