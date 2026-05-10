"""Async HTTP client for Wazuh Manager and Wazuh Indexer APIs.

Responsibilities:
1. **Authentication.** POST /security/user/authenticate with HTTP Basic, cache
   the returned JWT in memory, retry once with a fresh token on a 401.
2. **Pagination.** Wazuh caps ``limit`` per request; list operations walk the
   offset until the upstream total is exhausted.
3. **Error surface.** Network failures and Wazuh-side errors are wrapped in a
   single ``WazuhError`` so callers don't need to know httpx internals.
4. **Version split.** Agents/health come from the Manager API. Vulnerabilities
   in modern Wazuh releases are read from the Wazuh Indexer state index.

The frontend MUST NOT talk to Wazuh directly. Every Wazuh call goes through
this client so credentials, retries, and error shaping happen in exactly one
place.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.services.normalizers import extract_items, extract_total

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_PAGE_LIMIT = 500


class WazuhError(Exception):
    """Raised when the Wazuh API is unreachable or returns an error envelope."""


class WazuhClient:
    """Async Wazuh API client. Use as an async context manager."""

    def __init__(
        self,
        *,
        base_url: str,
        user: str,
        password: str,
        verify_tls: bool = False,
        indexer_url: str | None = None,
        indexer_user: str | None = None,
        indexer_password: str | None = None,
        indexer_verify_tls: bool = False,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self._user = user
        self._password = password
        self._token: str | None = None
        # Wazuh dev installs ship with a self-signed cert; ``verify_tls`` is
        # exposed so production deployments can flip it on once a real cert
        # is in place.
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            verify=verify_tls,
            timeout=timeout,
        )
        self._indexer_client: httpx.AsyncClient | None = None
        self._indexer_auth: httpx.BasicAuth | None = None
        if indexer_url and indexer_user and indexer_password:
            self._indexer_client = httpx.AsyncClient(
                base_url=indexer_url.rstrip("/"),
                verify=indexer_verify_tls,
                timeout=timeout,
            )
            self._indexer_auth = httpx.BasicAuth(indexer_user, indexer_password)

    # ----- lifecycle ----------------------------------------------------

    async def __aenter__(self) -> "WazuhClient":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()
        if self._indexer_client is not None:
            await self._indexer_client.aclose()

    # ----- authentication ----------------------------------------------

    async def _authenticate(self) -> str:
        """POST /security/user/authenticate?raw=true returns the JWT as plain text."""
        try:
            resp = await self._client.post(
                "/security/user/authenticate",
                params={"raw": "true"},
                auth=httpx.BasicAuth(self._user, self._password),
            )
        except httpx.HTTPError as exc:
            raise WazuhError(f"Wazuh auth failed: {exc}") from exc

        if resp.status_code != 200:
            raise WazuhError(
                f"Wazuh auth returned HTTP {resp.status_code}: {resp.text[:200]}"
            )
        token = resp.text.strip()
        if not token:
            raise WazuhError("Wazuh auth succeeded but returned empty token.")
        return token

    async def _ensure_token(self) -> str:
        if self._token is None:
            self._token = await self._authenticate()
        return self._token

    # ----- low-level request -------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Authenticated request with one-shot retry on 401 (token expiry)."""
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}

        try:
            resp = await self._client.request(method, path, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise WazuhError(f"Wazuh request to {path} failed: {exc}") from exc

        # Token expired mid-session? Re-auth once and retry.
        if resp.status_code == 401:
            self._token = None
            token = await self._ensure_token()
            headers["Authorization"] = f"Bearer {token}"
            try:
                resp = await self._client.request(method, path, params=params, headers=headers)
            except httpx.HTTPError as exc:
                raise WazuhError(f"Wazuh request to {path} failed after re-auth: {exc}") from exc

        if resp.status_code >= 400:
            raise WazuhError(
                f"Wazuh {method} {path} -> HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise WazuhError(f"Wazuh response was not JSON: {exc}") from exc

        # Wazuh returns 200 with an `error` field on logical failures
        # (e.g. agent doesn't exist). Surface those as WazuhError too.
        if isinstance(payload, dict) and payload.get("error", 0) not in (0, None):
            raise WazuhError(
                f"Wazuh {method} {path} returned error={payload.get('error')}: "
                f"{payload.get('message', 'no message')}"
            )

        return payload

    async def _indexer_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Authenticated request to the Wazuh Indexer (OpenSearch) API."""
        if self._indexer_client is None or self._indexer_auth is None:
            raise WazuhError(
                "Wazuh Indexer is not configured. Set WAZUH_INDEXER_URL, "
                "WAZUH_INDEXER_USER, and WAZUH_INDEXER_PASSWORD to sync "
                "vulnerabilities from Wazuh 4.8+."
            )

        try:
            resp = await self._indexer_client.request(
                method,
                path,
                params=params,
                json=json,
                auth=self._indexer_auth,
            )
        except httpx.HTTPError as exc:
            raise WazuhError(
                f"Wazuh Indexer request to {path} failed: {exc}"
            ) from exc

        if resp.status_code >= 400:
            raise WazuhError(
                f"Wazuh Indexer {method} {path} -> HTTP {resp.status_code}: "
                f"{resp.text[:300]}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise WazuhError(f"Wazuh Indexer response was not JSON: {exc}") from exc

        return payload

    # ----- public endpoints --------------------------------------------

    async def health(self) -> dict[str, Any]:
        """Round-trip GET /manager/info; raises WazuhError if unreachable."""
        return await self._request("GET", "/manager/info")

    async def list_agents(
        self, *, limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[dict[str, Any]]:
        """All agents, walking pagination until total_affected_items is reached."""
        return await self._paginate("GET", "/agents", limit=limit)

    async def list_vulnerabilities(
        self, agent_id: str, *, limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[dict[str, Any]]:
        """All vulnerabilities for one agent, walking pagination.

        Modern Wazuh stores vulnerability state in the Indexer instead of the
        Manager API. If indexer settings are present, use that source. If not,
        fall back to the legacy Manager endpoint so old lab installations still
        fail gracefully with a clear message.
        """
        if self._indexer_client is not None:
            return await self._list_vulnerabilities_from_indexer(
                agent_id, limit=limit,
            )

        try:
            return await self._paginate(
                "GET", f"/vulnerability/{agent_id}", limit=limit,
            )
        except WazuhError as exc:
            if "HTTP 404" in str(exc):
                raise WazuhError(
                    "The Wazuh Manager vulnerability endpoint is unavailable. "
                    "Configure WAZUH_INDEXER_* settings and query the Wazuh "
                    "Indexer vulnerability state index instead."
                ) from exc
            raise

    # ----- pagination helper -------------------------------------------

    async def _paginate(
        self, method: str, path: str, *, limit: int,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        offset = 0
        while True:
            payload = await self._request(
                method, path, params={"limit": limit, "offset": offset},
            )
            items = extract_items(payload)
            total = extract_total(payload)
            out.extend(items)
            # Stop conditions: page came back empty OR we've fetched everything
            # the server says exists. The empty-page check guards against bad
            # ``total`` values causing infinite loops.
            if not items or len(out) >= total:
                break
            offset += limit
        return out

    async def _list_vulnerabilities_from_indexer(
        self, agent_id: str, *, limit: int,
    ) -> list[dict[str, Any]]:
        """Read vulnerability inventory from ``wazuh-states-vulnerabilities*``."""
        out: list[dict[str, Any]] = []
        offset = 0

        while True:
            payload = await self._indexer_request(
                "POST",
                "/wazuh-states-vulnerabilities*/_search",
                params={
                    "ignore_unavailable": "true",
                    "allow_no_indices": "true",
                },
                json={
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"agent.id": agent_id}},
                            ],
                        },
                    },
                    "from": offset,
                    "size": limit,
                    "sort": [
                        {
                            "vulnerability.detected_at": {
                                "order": "desc",
                                "unmapped_type": "date",
                            },
                        },
                    ],
                },
            )

            hits_envelope = payload.get("hits") or {}
            hits = hits_envelope.get("hits") or []
            if not isinstance(hits, list):
                hits = []

            for hit in hits:
                if not isinstance(hit, dict):
                    continue
                source = hit.get("_source") or {}
                if not isinstance(source, dict):
                    continue
                item = dict(source)
                # Preserve index metadata for audit/debug without depending on
                # OpenSearch response shape elsewhere in the codebase.
                item["_index"] = hit.get("_index")
                item["_id"] = hit.get("_id")
                out.append(item)

            total_raw = hits_envelope.get("total", 0)
            if isinstance(total_raw, dict):
                total = int(total_raw.get("value") or 0)
            else:
                total = int(total_raw or 0)

            if not hits or len(out) >= total:
                break
            offset += limit

        return out


# ----- factory -------------------------------------------------------------

def get_wazuh_client() -> WazuhClient:
    """Build a WazuhClient from current Settings."""
    s = get_settings()
    return WazuhClient(
        base_url=s.wazuh_api_url,
        user=s.wazuh_api_user,
        password=s.wazuh_api_password,
        verify_tls=s.wazuh_verify_tls,
        indexer_url=s.wazuh_indexer_url,
        indexer_user=s.wazuh_indexer_user,
        indexer_password=s.wazuh_indexer_password,
        indexer_verify_tls=s.wazuh_indexer_verify_tls,
    )
