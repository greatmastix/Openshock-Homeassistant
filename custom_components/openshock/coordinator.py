"""Data update coordinator for OpenShock."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OpenShockApiClient, OpenShockApiError
from .const import DOMAIN
from .signalr import OpenShockSignalRClient

_LOGGER = logging.getLogger(__name__)


class OpenShockDataCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator that polls OpenShock for shocker state."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: OpenShockApiClient,
        poll_interval: int,
        config_entry_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="OpenShock",
            update_interval=timedelta(seconds=poll_interval),
        )
        self.api = api
        self._config_entry_id = config_entry_id
        self._signalr_client: OpenShockSignalRClient | None = None
        self._signalr_task = None

    async def async_start_signalr(self) -> None:
        """Start the OpenShock SignalR user hub listener."""
        if self._signalr_task is not None:
            return

        self._signalr_client = OpenShockSignalRClient(
            session=self.api.session,
            url=self.api.signalr_user_hub_url,
            headers=self.api.headers,
            message_handler=self._async_handle_signalr_message,
        )
        self._signalr_task = self.hass.async_create_task(
            self._signalr_client.run(),
            name="openshock_signalr",
        )

    async def async_stop_signalr(self) -> None:
        """Stop the OpenShock SignalR user hub listener."""
        if self._signalr_client is not None:
            self._signalr_client.stop()

        if self._signalr_task is not None:
            self._signalr_task.cancel()
            with suppress(TimeoutError, asyncio.CancelledError):
                await self._signalr_task
            self._signalr_task = None

        self._signalr_client = None

    async def _async_handle_signalr_message(self, target: str, arguments: list[Any]) -> None:
        """Handle server-to-client SignalR invocations."""
        if target == "DeviceStatus":
            self._async_apply_device_status(arguments)
            return

        if target == "DeviceUpdate":
            await self.async_request_refresh()
            return

        _LOGGER.debug("Ignoring OpenShock SignalR message %s", target)

    def _async_apply_device_status(self, arguments: list[Any]) -> None:
        """Apply device online states from SignalR to existing shocker data."""
        if not self.data or not arguments or not isinstance(arguments[0], list):
            return

        statuses: dict[str, dict[str, Any]] = {}
        for state in arguments[0]:
            if not isinstance(state, dict):
                continue
            device_id = state.get("deviceId") or state.get("id")
            if device_id is not None:
                statuses[str(device_id)] = state

        if not statuses:
            return

        changed = False
        updated_data: list[dict[str, Any]] = []
        for shocker in self.data:
            updated = dict(shocker)
            hub_id = updated.get("hub_id") or updated.get("hubId") or updated.get("deviceId")
            state = statuses.get(str(hub_id)) if hub_id is not None else None
            if state is not None:
                online = state.get("online")
                if online is not None:
                    status = "online" if online else "offline"
                    if updated.get("status") != status:
                        updated["status"] = status
                        changed = True
                firmware_version = state.get("firmwareVersion")
                if firmware_version is not None and updated.get("firmwareVersion") != firmware_version:
                    updated["firmwareVersion"] = firmware_version
                    changed = True
            updated_data.append(updated)

        if changed:
            self.async_set_updated_data(updated_data)

    @staticmethod
    def _extract_shocker_id(item: dict[str, Any]) -> str | None:
        for key in ("id", "shockerId", "shocker_id", "uuid"):
            value = item.get(key)
            if value:
                return str(value)
        return None

    async def _async_remove_deleted_shocker_entities(self, removed_ids: set[str]) -> None:
        """Remove entities/devices for shockers that no longer exist."""
        if not removed_ids:
            return

        entity_registry = er.async_get(self.hass)
        for entry in list(entity_registry.entities.values()):
            if entry.platform != DOMAIN or entry.config_entry_id != self._config_entry_id:
                continue

            if any(
                entry.unique_id == shocker_id or entry.unique_id.startswith(f"{shocker_id}_")
                for shocker_id in removed_ids
            ):
                entity_registry.async_remove(entry.entity_id)

        device_registry = dr.async_get(self.hass)
        for device in list(device_registry.devices.values()):
            if self._config_entry_id not in device.config_entries:
                continue

            if any((DOMAIN, shocker_id) in device.identifiers for shocker_id in removed_ids):
                has_remaining_entities = any(
                    entity.device_id == device.id and entity.config_entry_id == self._config_entry_id
                    for entity in entity_registry.entities.values()
                )
                if has_remaining_entities:
                    device_registry.async_update_device(
                        device_id=device.id,
                        remove_config_entry_id=self._config_entry_id,
                    )
                else:
                    device_registry.async_remove_device(device.id)

    async def async_prune_stale_registry_entries(self) -> None:
        """Prune stale entities/devices after startup reloads."""
        current_ids = {
            shocker_id
            for item in (self.data or [])
            if (shocker_id := self._extract_shocker_id(item)) is not None
        }

        device_registry = dr.async_get(self.hass)
        stale_device_ids = {
            device.id
            for device in device_registry.devices.values()
            if self._config_entry_id in device.config_entries
            and any(identifier[0] == DOMAIN and identifier[1] not in current_ids for identifier in device.identifiers)
        }

        if not stale_device_ids:
            return

        entity_registry = er.async_get(self.hass)
        for entry in list(entity_registry.entities.values()):
            if entry.platform != DOMAIN or entry.config_entry_id != self._config_entry_id:
                continue
            if entry.device_id in stale_device_ids:
                entity_registry.async_remove(entry.entity_id)

        for device_id in stale_device_ids:
            device_registry.async_remove_device(device_id)

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            data = await self.api.get_shockers()

            previous = {
                shocker_id
                for item in (self.data or [])
                if (shocker_id := self._extract_shocker_id(item)) is not None
            }
            current = {
                shocker_id
                for item in data
                if (shocker_id := self._extract_shocker_id(item)) is not None
            }
            await self._async_remove_deleted_shocker_entities(previous - current)

            return data
        except OpenShockApiError as err:
            raise UpdateFailed(str(err)) from err
