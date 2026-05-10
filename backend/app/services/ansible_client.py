"""Async HTTP client for the Ansible Automation Controller (AWX) REST API.

Responsibilities:
1. **Authentication.** Bearer token if ``AWX_API_TOKEN`` is set (recommended for
   service accounts), otherwise HTTP Basic with ``AWX_API_USER`` /
   ``AWX_API_PASSWORD``.
2. **Launching.** ``POST /api/v2/job_templates/{id}/launch/`` with the
   policy-built ``extra_vars`` payload.
3. **Polling.** ``GET /api/v2/jobs/{id}/`` so the remediation service can wait
   for completion before triggering Wazuh re-verification.

The frontend MUST NOT talk to AWX directly. SSH and WinRM credentials live in
AWX itself (or its vault) and never traverse the backend, but our backend is
still the only thing in the platform that ever calls AWX — which keeps the
attack surface and the audit trail in one place.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class AnsibleError(Exception):
    """Raised when AWX is unreachable or returns an error response."""


class AnsibleClient:
    """Async AWX API client. Use as an async context manager.

    Usage::

        async with get_ansible_client() as awx:
            await awx.health()
            launch = await awx.launch_job_template(12, extra_vars={...})
            job_id = extract_job_id(launch)
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None = None,
        user: str | None = None,
        password: str | None = None,
        verify_tls: bool = False,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        # Pick auth scheme once at construction. Bearer wins because that's
        # what AWX recommends for service accounts; basic auth is the fallback.
        if token:
            headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
            auth: httpx.Auth | None = None
        elif user and password:
            headers = {}
            auth = httpx.BasicAuth(user, password)
        else:
            raise ValueError(
                "AnsibleClient requires either AWX_API_TOKEN or "
                "AWX_API_USER + AWX_API_PASSWORD."
            )

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            verify=verify_tls,
            timeout=timeout,
            auth=auth,
            headers={**headers, "Accept": "application/json"},
        )

    # ----- lifecycle ----------------------------------------------------

    async def __aenter__(self) -> "AnsibleClient":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ----- low-level request -------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Issue a request and return the parsed JSON body, or raise AnsibleError."""
        try:
            resp = await self._client.request(method, path, params=params, json=json)
        except httpx.HTTPError as exc:
            raise AnsibleError(f"AWX {method} {path} failed: {exc}") from exc

        if resp.status_code >= 400:
            raise AnsibleError(
                f"AWX {method} {path} -> HTTP {resp.status_code}: {resp.text[:300]}"
            )

        # 204 No Content / empty success bodies — surface as empty dict so
        # callers don't need to special-case them.
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError as exc:
            raise AnsibleError(f"AWX response was not JSON: {exc}") from exc

    # ----- public endpoints --------------------------------------------

    async def health(self) -> dict[str, Any]:
        """``GET /api/v2/ping/`` — used by the integrations health route."""
        return await self._request("GET", "/api/v2/ping/")

    async def launch_job_template(
        self,
        job_template_id: int,
        *,
        extra_vars: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Launch an approved AWX job template.

        ``extra_vars`` is the policy-built context (asset hostname, CVE,
        package, etc.) that the playbook consumes via Jinja substitution.
        AWX returns the newly-created job; the job id can be pulled out with
        :func:`extract_job_id`.
        """
        body: dict[str, Any] = {}
        if extra_vars:
            body["extra_vars"] = extra_vars
        return await self._request(
            "POST",
            f"/api/v2/job_templates/{job_template_id}/launch/",
            json=body,
        )

    async def get_job(self, job_id: int) -> dict[str, Any]:
        """Fetch a job's current state, including ``status`` and stdout snippet."""
        return await self._request("GET", f"/api/v2/jobs/{job_id}/")


# ----- helpers --------------------------------------------------------------

def extract_job_id(launch_response: dict[str, Any]) -> int | None:
    """Pull the new job id out of an AWX launch response.

    AWX has used both ``id`` (newer releases) and ``job`` (older releases) as
    the field name. Returns ``None`` if neither is present so the caller can
    surface a clear error rather than a KeyError mid-transaction.
    """
    raw = launch_response.get("id") or launch_response.get("job")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ----- factory --------------------------------------------------------------

def get_ansible_client() -> AnsibleClient:
    """Build an AnsibleClient from current Settings."""
    s = get_settings()
    return AnsibleClient(
        base_url=s.awx_api_url,
        token=s.awx_api_token,
        user=s.awx_api_user,
        password=s.awx_api_password,
        verify_tls=s.awx_verify_tls,
    )
