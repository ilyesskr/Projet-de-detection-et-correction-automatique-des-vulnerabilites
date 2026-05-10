"""Health probes for the external systems we integrate with.

These do **real** round-trips (Wazuh ``/manager/info``, AWX ``/api/v2/ping/``)
so the operator UI can display "wazuh / awx reachable" with confidence, not
just based on whether config values look set.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_ansible, get_wazuh, require_permission
from app.core.permissions import Permission
from app.schemas.common import HealthResponse
from app.services.ansible_client import AnsibleClient, AnsibleError
from app.services.wazuh_client import WazuhClient, WazuhError

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_permission(Permission.INTEGRATIONS_READ))],
)


@router.get("/wazuh/health", response_model=HealthResponse)
async def wazuh_health(wazuh: WazuhClient = Depends(get_wazuh)) -> HealthResponse:
    try:
        await wazuh.health()
    except WazuhError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"wazuh: {exc}",
        )
    return HealthResponse(status="ok", detail="wazuh reachable")


@router.get("/ansible/health", response_model=HealthResponse)
async def ansible_health(awx: AnsibleClient = Depends(get_ansible)) -> HealthResponse:
    try:
        await awx.health()
    except AnsibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"awx: {exc}",
        )
    return HealthResponse(status="ok", detail="awx reachable")
