"""Async API client for OpenShock."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

REQUEST_TIMEOUT = 15
USER_AGENT_PRODUCT = "OpenShock-HomeAssistant"

AUTH_ERROR_STATUSES = frozenset({401, 403})


class OpenShockApiError(Exception):
    """Raised when OpenShock API fails."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status

    @property
    def can_try_other_endpoint(self) -> bool:
        """Return True if the server rejected the request without acting on it.

        Only a 4xx response (other than an auth error) proves that. Timeouts,
        connection errors and 5xx responses are ambiguous: a control request may
        still have reached the shocker, so resending it to another endpoint could
        deliver the same shock twice.
        """
        return (
            self.status is not None
            and 400 <= self.status < 500
            and self.status not in AUTH_ERROR_STATUSES
        )


class OpenShockApiClient:
    """OpenShock API client."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        api_key: str,
        user_agent: str = USER_AGENT_PRODUCT,
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

    @property
    def headers(self) -> dict[str, str]:
        """Return a copy of the API headers."""
        return dict(self._headers)

    @property
    def session(self) -> ClientSession:
        """Return the shared aiohttp session."""
        return self._session

    @property
    def signalr_user_hub_url(self) -> str:
        """Return the SignalR user hub websocket URL."""
        parsed = urlsplit(self._base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return urlunsplit((scheme, parsed.netloc, "/1/hubs/user", "", ""))

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
            async with self._session.request(method, url, headers=self._headers, json=json_body, timeout=ClientTimeout(total=REQUEST_TIMEOUT)) as resp:
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
        except (ClientError, TimeoutError) as err:
            raise OpenShockApiError(f"Request failed for {path}: {err!r}") from err

    async def test_connection(self) -> None:
        await self.get_shockers()

    @staticmethod
    def _extract_shocker_id(item: dict[str, Any]) -> str | None:
        for key in ("shockerId", "shocker_id", "uuid", "id"):
            value = item.get(key)
            if not value:
                continue

            candidate = str(value).strip()
            try:
                return str(UUID(candidate))
            except ValueError:
                continue
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
            except OpenShockApiError as err:
                if not err.can_try_other_endpoint:
                    raise
                last_exc = err
                continue

            shockers = self._normalize_shockers(payload)
            if shockers:
                return shockers

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
        if mapped_type == "Stop":
            # OpenShock control schema requires intensity/duration for all control types.
            control["intensity"] = 0
            control["duration"] = 300
        else:
            control["intensity"] = max(1, min(100, int(intensity if intensity is not None else 50)))
            control["duration"] = max(300, min(65535, int(duration_ms if duration_ms is not None else 1000)))

        last_exc: Exception | None = None
        for path in ("/2/shockers/control", "/1/shockers/control"):
            payload: dict[str, Any] | list[dict[str, Any]]
            if path.startswith("/1/"):
                payload = [control]
            else:
                payload = {"shocks": [control]}
            try:
                await self._request("POST", path, json_body=payload)
                return
            except OpenShockApiError as err:
                # Never resend a command after a timeout or server error.
                if not err.can_try_other_endpoint:
                    raise
                last_exc = err

        if last_exc:
            raise last_exc

    async def stop_all(self) -> None:
        """Stop all owned shockers.

        The stop is sent to every shocker, concurrently, even if some of them
        fail (e.g. one hub is offline), so one failure cannot leave the other
        shockers running. Afterwards a single OpenShockApiError names every
        shocker that could not be stopped.
        """
        # Shocker id -> label for error messages. Keyed by id so a shocker
        # listed twice is only sent one stop.
        targets: dict[str, str] = {}
        for shocker in await self.get_shockers():
            if (shocker_id := self._extract_shocker_id(shocker)) is None:
                continue
            name = shocker.get("name") or shocker.get("label")
            targets.setdefault(shocker_id, f"{name} ({shocker_id})" if name else shocker_id)

        results = await asyncio.gather(
            *(
                self.send_command(
                    shocker_id=shocker_id,
                    command="stop",
                    intensity=None,
                    duration_ms=None,
                )
                for shocker_id in targets
            ),
            return_exceptions=True,
        )

        failures: list[str] = []
        for label, result in zip(targets.values(), results):
            if isinstance(result, OpenShockApiError):
                failures.append(f"{label}: {result}")
            elif isinstance(result, BaseException):
                # Not an API failure (e.g. a bug); every stop has already been sent.
                raise result

        if failures:
            raise OpenShockApiError(
                f"Stop failed for {len(failures)} of {len(targets)} shockers: "
                + ", ".join(failures)
            )
