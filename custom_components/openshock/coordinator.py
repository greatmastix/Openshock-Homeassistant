"""Data update coordinator for OpenShock."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
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
        """Remove entities for shockers that no longer exist."""
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
