"""Backend + database health probe.

The *public* liveness route (``GET /health``) is wired in ``main.py``; this
file provides the protected ``GET /api/v1/health`` which additionally proves
the database is reachable.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse, dependencies=[Depends(get_current_user)])
def health(db: Session = Depends(get_db)) -> HealthResponse:
    """Round-trips a ``SELECT 1`` to verify the DB is reachable.

    Requires authentication but no specific permission — any logged-in user
    can probe DB connectivity.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - intentionally broad for health checks
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unreachable: {exc}",
        )
    return HealthResponse(status="ok", detail="postgres reachable")
