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
from src.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="File exchange", version="0.2.0")

    # CORS allow-list intentionally narrow — the frontend runs on a fixed
    # localhost port in dev. Production deployments should override via
    # configuration; the broader wildcard policy from the original app
    # was unnecessarily permissive.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.include_router(files_router.router)
    app.include_router(alerts_router.router)

    register_exception_handlers(app)

    return app


app = create_app()
