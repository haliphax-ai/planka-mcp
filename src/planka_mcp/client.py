"""HTTP client for the Planka REST API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class PlankaApiFormatError(RuntimeError):
    """Raised when Planka returns a non-JSON body where JSON was expected."""

    def __init__(
        self, method: str, url: str, status_code: int, content_type: str, snippet: str
    ) -> None:
        self.method = method
        self.url = url
        self.status_code = status_code
        self.content_type = content_type
        self.snippet = snippet
        super().__init__(
            f"{method} {url} returned {status_code} with content-type {content_type!r}; "
            f"body: {snippet}"
        )


class PlankaClient:
    """Async HTTP client wrapping the Planka REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
    ) -> None:
        self._base_url = (
            base_url or os.environ.get("PLANKA_BASE_URL", "http://localhost:1337")
        ).rstrip("/")
        self._api_token = api_token or os.environ.get("PLANKA_API_TOKEN", "")
        self._client: httpx.AsyncClient | None = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self._api_token,
        }

    def _api_url(self, path: str) -> str:
        """Build the full API URL for a given path."""
        return f"{self._base_url}/api/{path.lstrip('/')}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # --- Generic HTTP methods ---

    def _parse_json(self, resp: httpx.Response) -> dict[str, Any]:
        """Parse a response body, raising a descriptive error for non-JSON bodies."""
        content_type = resp.headers.get("content-type", "")
        if "json" not in content_type.lower():
            body = resp.text[:120].replace("\n", " ")
            raise PlankaApiFormatError(
                resp.request.method,
                str(resp.request.url),
                resp.status_code,
                content_type or "(none)",
                repr(body),
            )
        return resp.json()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(self._api_url(path), headers=self._headers, params=params)
        resp.raise_for_status()
        return self._parse_json(resp)

    async def post(
        self,
        path: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            self._api_url(path), headers=self._headers, json=data, params=params
        )
        resp.raise_for_status()
        return self._parse_json(resp)

    async def patch(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.patch(self._api_url(path), headers=self._headers, json=data)
        resp.raise_for_status()
        return self._parse_json(resp)

    async def delete(self, path: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.delete(self._api_url(path), headers=self._headers)
        resp.raise_for_status()
        return self._parse_json(resp)

    async def upload(
        self,
        path: str,
        file_path: str,
        file_name: str,
        extra_fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload a file via multipart form data."""
        client = await self._get_client()
        headers = {"X-Api-Key": self._api_token}
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f)}
            data = extra_fields or {}
            resp = await client.post(self._api_url(path), headers=headers, files=files, data=data)
        resp.raise_for_status()
        return self._parse_json(resp)
