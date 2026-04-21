"""Async API client for OpenShock."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession


class OpenShockApiError(Exception):
    """Raised when OpenShock API fails."""


class OpenShockApiClient:
    """OpenShock API client with endpoint fallback support."""

    def __init__(self, session: ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(method, url, headers=self._headers, json=json_body) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise OpenShockApiError(f"HTTP {resp.status} for {path}: {text[:250]}")

                if resp.content_type and "json" in resp.content_type:
                    return await resp.json()
                return await resp.text()
        except ClientError as err:
            raise OpenShockApiError(f"Request failed for {path}: {err}") from err

    async def test_connection(self) -> None:
        await self.get_shockers()

    async def get_shockers(self) -> list[dict[str, Any]]:
        """Fetch shockers using common endpoint variants."""
        last_exc: Exception | None = None
        for path in ("/1/shockers", "/shockers"):
            try:
                payload = await self._request("GET", path)
                if isinstance(payload, list):
                    return payload
                if isinstance(payload, dict):
                    for key in ("data", "shockers", "items"):
                        value = payload.get(key)
                        if isinstance(value, list):
                            return value
                return []
            except OpenShockApiError as err:
                last_exc = err
        if last_exc:
            raise last_exc
        return []

    async def send_command(
        self,
        *,
        shocker_id: str,
        command: str,
        intensity: int | None,
        duration_ms: int | None,
    ) -> None:
        """Send a control command with fallback payload/endpoint formats."""

        payloads = [
            {
                "shockerId": shocker_id,
                "type": command.capitalize(),
                "intensity": intensity,
                "duration": duration_ms,
            },
            {
                "id": shocker_id,
                "command": command,
                "intensity": intensity,
                "durationMs": duration_ms,
            },
        ]

        attempts = [
            ("POST", f"/1/shockers/{shocker_id}/control"),
            ("POST", "/1/shockers/control"),
            ("POST", "/shockers/control"),
        ]

        last_exc: Exception | None = None
        for method, path in attempts:
            for payload in payloads:
                clean_payload = {k: v for k, v in payload.items() if v is not None}
                try:
                    await self._request(method, path, json_body=clean_payload)
                    return
                except OpenShockApiError as err:
                    last_exc = err

        if last_exc:
            raise last_exc

    async def stop_all(self) -> None:
        last_exc: Exception | None = None
        for path in ("/1/shockers/stop", "/shockers/stop"):
            try:
                await self._request("POST", path, json_body={})
                return
            except OpenShockApiError as err:
                last_exc = err
        if last_exc:
            raise last_exc
