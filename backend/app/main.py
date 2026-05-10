"""FastAPI application entrypoint.

Run locally with::

    cd backend && uvicorn app.main:app --reload --port 8000

OpenAPI / Swagger UI lives at ``/docs``. The platform API is mounted under
``/api/v1``: ``/auth/login`` is public, every other route declares its own
JWT + permission requirement via ``app.api.dependencies``.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.auth import router as auth_router
from app.core.config import get_settings
from app.schemas.common import HealthResponse


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hook.

    Currently a no-op; kept here so future startup work (warm Redis pool,
    schedule background tasks, ...) has a single home.
    """
    yield


_settings = get_settings()

app = FastAPI(
    title=_settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — only enable when explicitly configured. An empty list keeps the
# default browser same-origin policy in effect during local dev.
if _settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ----- Public routes --------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["health"])
def public_health() -> HealthResponse:
    """Liveness probe: is the FastAPI process up?

    Deliberately does not touch the database — that's what
    ``GET /api/v1/health`` is for. This route is safe to hit from any
    load-balancer / uptime monitor without credentials.
    """
    return HealthResponse(status="ok", detail=_settings.app_name)


# ----- Auth (login is public; /me has its own JWT dependency) --------------

app.include_router(auth_router, prefix=_settings.api_prefix)


# ----- Protected platform API ----------------------------------------------

# Each route under here declares its own ``require_permission`` /
# ``get_current_user`` dependency. There is no outer gate; the auth surface
# is per-route so unauthenticated calls fail at the route, not at the prefix.
app.include_router(api_router, prefix=_settings.api_prefix)
