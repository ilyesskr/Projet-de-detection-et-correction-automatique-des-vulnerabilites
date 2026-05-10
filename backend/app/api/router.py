"""Aggregate all resource routers under one APIRouter.

``main.py`` mounts this at ``settings.api_prefix`` (``/api/v1`` by default).
Each route declares its own JWT/RBAC dependency.
"""

from fastapi import APIRouter

from app.api.routes import (
    assets,
    audit,
    dashboard,
    health,
    integrations,
    remediation,
    sync,
    users,
    vulnerabilities,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(integrations.router)
api_router.include_router(sync.router)
api_router.include_router(assets.router)
api_router.include_router(vulnerabilities.router)
api_router.include_router(remediation.router)
api_router.include_router(audit.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
