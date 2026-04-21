"""The OpenShock integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenShockApiClient, OpenShockApiError
from .const import (
    ATTR_COMMAND,
    ATTR_DURATION_MS,
    ATTR_INTENSITY,
    ATTR_SHOCKER_ID,
    COMMAND_STOP,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_POLL_INTERVAL,
    DATA_COORDINATOR,
    DATA_DEFAULTS,
    DEFAULT_DURATION_MS,
    DEFAULT_INTENSITY,
    DOMAIN,
    PLATFORMS,
    SERVICE_SEND_COMMAND,
    SERVICE_STOP_ALL,
    VALID_COMMANDS,
)
from .coordinator import OpenShockDataCoordinator

SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SHOCKER_ID): cv.string,
        vol.Required(ATTR_COMMAND): vol.In(VALID_COMMANDS),
        vol.Optional(ATTR_INTENSITY): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional(ATTR_DURATION_MS): vol.All(vol.Coerce(int), vol.Range(min=100, max=30000)),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenShock from a config entry."""
    session = async_get_clientsession(hass)
    api = OpenShockApiClient(
        session=session,
        base_url=entry.data[CONF_BASE_URL],
        api_key=entry.data[CONF_API_KEY],
    )

    coordinator = OpenShockDataCoordinator(
        hass=hass,
        api=api,
        poll_interval=entry.options.get(CONF_POLL_INTERVAL, entry.data[CONF_POLL_INTERVAL]),
        config_entry_id=entry.entry_id,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = {DATA_COORDINATOR: coordinator, DATA_DEFAULTS: {}}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_send_command(call: ServiceCall) -> None:
        shocker_id = call.data[ATTR_SHOCKER_ID]
        command = call.data[ATTR_COMMAND]

        defaults = entry.runtime_data[DATA_DEFAULTS].get(shocker_id, {})
        intensity = call.data.get(ATTR_INTENSITY, defaults.get(ATTR_INTENSITY, DEFAULT_INTENSITY))
        duration_ms = call.data.get(ATTR_DURATION_MS, defaults.get(ATTR_DURATION_MS, DEFAULT_DURATION_MS))

        if command == COMMAND_STOP:
            intensity = None
            duration_ms = None

        try:
            await api.send_command(
                shocker_id=shocker_id,
                command=command,
                intensity=intensity,
                duration_ms=duration_ms,
            )
        except OpenShockApiError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_stop_all(_: ServiceCall) -> None:
        try:
            await api.stop_all()
        except OpenShockApiError as err:
            raise HomeAssistantError(str(err)) from err

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_COMMAND,
            async_send_command,
            schema=SEND_COMMAND_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_STOP_ALL):
        hass.services.async_register(DOMAIN, SERVICE_STOP_ALL, async_stop_all)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload OpenShock config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded and len(hass.config_entries.async_entries(DOMAIN)) <= 1:
        hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
        hass.services.async_remove(DOMAIN, SERVICE_STOP_ALL)

    return unloaded
