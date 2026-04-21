"""Data update coordinator for OpenShock."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OpenShockApiClient, OpenShockApiError
from .const import DOMAIN


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


import logging

_LOGGER = logging.getLogger(__name__)
