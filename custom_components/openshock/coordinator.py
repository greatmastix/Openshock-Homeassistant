"""Data update coordinator for OpenShock."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OpenShockApiClient, OpenShockApiError


class OpenShockDataCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator that polls OpenShock for shocker state."""

    def __init__(self, hass: HomeAssistant, api: OpenShockApiClient, poll_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="OpenShock",
            update_interval=timedelta(seconds=poll_interval),
        )
        self.api = api

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            return await self.api.get_shockers()
        except OpenShockApiError as err:
            raise UpdateFailed(str(err)) from err


import logging

_LOGGER = logging.getLogger(__name__)
