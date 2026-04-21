"""Async API client for OpenShock."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession


class OpenShockApiError(Exception):
    """Raised when OpenShock API fails."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class OpenShockApiClient:
    """OpenShock API client."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        api_key: str,
        user_agent: str = "OpenShock-HomeAssistant/0.2.3",
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        token = api_key.removeprefix("Bearer ").strip()
        self._headers = {
            "OpenShockToken": token,
            "Open-Shock-Token": token,
            "Accept": "application/json",
            "User-Agent": user_agent,
        }

    @staticmethod
    def _error_message(payload: Any, fallback: str) -> str:
        if isinstance(payload, dict):
            for key in ("message", "detail", "title", "error"):
                value = payload.get(key)
                if value:
                    return str(value)
        return fallback

    @staticmethod
    def _unwrap_data(payload: Any) -> Any:
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    async def _request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(method, url, headers=self._headers, json=json_body) as resp:
                content_type = (resp.content_type or "").lower()
                if "json" in content_type:
                    payload: Any = await resp.json(content_type=None)
                else:
                    payload = await resp.text()

                if resp.status >= 400:
                    message = self._error_message(payload, str(payload)[:250])
                    raise OpenShockApiError(f"HTTP {resp.status} for {path}: {message}", status=resp.status)

                return payload
        except ClientResponseError as err:
            raise OpenShockApiError(f"Request failed for {path}: {err}", status=err.status) from err
        except ClientError as err:
            raise OpenShockApiError(f"Request failed for {path}: {err}") from err

    async def test_connection(self) -> None:
        await self.get_shockers()

    @staticmethod
    def _extract_shocker_id(item: dict[str, Any]) -> str | None:
        for key in ("id", "shockerId", "shocker_id", "uuid"):
            value = item.get(key)
            if value:
                return str(value)
        return None

    def _normalize_shockers(self, payload: Any) -> list[dict[str, Any]]:
        """Normalize possible API response shapes to a flat shocker list."""
        payload = self._unwrap_data(payload)

        if isinstance(payload, dict):
            for key in ("shockers", "items", "devices", "hubs"):
                value = payload.get(key)
                if isinstance(value, list):
                    return self._normalize_shockers(value)
            return []

        if not isinstance(payload, list):
            return []

        flat: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue

            nested = item.get("shockers")
            if isinstance(nested, list):
                hub_id = item.get("id") or item.get("hubId") or item.get("deviceId")
                hub_name = item.get("name") or item.get("hubName") or item.get("deviceName")
                for shocker in nested:
                    if not isinstance(shocker, dict):
                        continue
                    parsed = dict(shocker)
                    if hub_id is not None:
                        parsed.setdefault("hub_id", str(hub_id))
                    if hub_name is not None:
                        parsed.setdefault("hub_name", str(hub_name))
                    flat.append(parsed)
                continue

            if self._extract_shocker_id(item):
                flat.append(item)

        return flat

    async def get_shockers(self) -> list[dict[str, Any]]:
        """Fetch owned shockers."""
        last_exc: Exception | None = None
        for path in ("/1/shockers/own", "/1/shockers", "/shockers"):
            try:
                payload = await self._request("GET", path)
                shockers = self._normalize_shockers(payload)
                if shockers:
                    return shockers
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
        """Send a control command."""
        mapped_type = {
            "shock": "Shock",
            "vibrate": "Vibrate",
            "sound": "Sound",
            "beep": "Sound",
            "stop": "Stop",
        }.get(command.lower(), command)

        control: dict[str, Any] = {"id": shocker_id, "type": mapped_type}
        if mapped_type != "Stop":
            control["intensity"] = max(1, min(100, int(intensity if intensity is not None else 50)))
            control["duration"] = max(100, min(30000, int(duration_ms if duration_ms is not None else 1000)))

        payload = {"shocks": [control]}

        last_exc: Exception | None = None
        for path in ("/2/shockers/control", "/1/shockers/control"):
            try:
                await self._request("POST", path, json_body=payload)
                return
            except OpenShockApiError as err:
                last_exc = err

        if last_exc:
            raise last_exc

    async def stop_all(self) -> None:
        """Stop all owned shockers."""
        shockers = await self.get_shockers()
        for shocker in shockers:
            shocker_id = self._extract_shocker_id(shocker)
            if shocker_id:
                await self.send_command(
                    shocker_id=shocker_id,
                    command="stop",
                    intensity=None,
                    duration_ms=None,
                )
