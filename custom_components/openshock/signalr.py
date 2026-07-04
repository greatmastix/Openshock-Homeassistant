"""Minimal SignalR websocket client for OpenShock."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import ClientError, ClientSession, WSMsgType

_LOGGER = logging.getLogger(__name__)

SIGNALR_RECORD_SEPARATOR = "\x1e"


class OpenShockSignalRClient:
    """Connect to the OpenShock SignalR user hub over websockets."""

    def __init__(
        self,
        session: ClientSession,
        url: str,
        headers: dict[str, str],
        message_handler: Callable[[str, list[Any]], Awaitable[None]],
    ) -> None:
        self._session = session
        self._url = url
        self._headers = headers
        self._message_handler = message_handler
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        """Request the websocket loop to stop."""
        self._stop_event.set()

    async def run(self) -> None:
        """Run the reconnecting SignalR websocket loop."""
        reconnect_delay = 1

        while not self._stop_event.is_set():
            try:
                await self._run_once()
                reconnect_delay = 1
            except asyncio.CancelledError:
                raise
            except (ClientError, TimeoutError, OSError, ValueError) as err:
                if self._stop_event.is_set():
                    break
                _LOGGER.warning("OpenShock SignalR websocket disconnected: %s", err)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=reconnect_delay)
            except TimeoutError:
                reconnect_delay = min(reconnect_delay * 2, 60)

    async def _run_once(self) -> None:
        async with self._session.ws_connect(
            self._url,
            headers=self._headers,
            heartbeat=30,
        ) as ws:
            await ws.send_str(json.dumps({"protocol": "json", "version": 1}) + SIGNALR_RECORD_SEPARATOR)

            async for msg in ws:
                if self._stop_event.is_set():
                    await ws.close()
                    break
                if msg.type == WSMsgType.TEXT:
                    await self._handle_text(msg.data)
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                    break

    async def _handle_text(self, data: str) -> None:
        for raw_message in data.split(SIGNALR_RECORD_SEPARATOR):
            if not raw_message:
                continue

            message = json.loads(raw_message)
            if message.get("type") != 1:
                continue

            target = message.get("target")
            arguments = message.get("arguments", [])
            if isinstance(target, str) and isinstance(arguments, list):
                await self._message_handler(target, arguments)
