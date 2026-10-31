"""The OpenShock integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import USER_AGENT_PRODUCT, OpenShockApiClient
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_POLL_INTERVAL,
    DATA_COORDINATOR,
    DATA_DEFAULTS,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MIN_POLL_INTERVAL,
    PLATFORMS,
)
from .coordinator import OpenShockDataCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_create_api_client(hass: HomeAssistant, base_url: str, api_key: str) -> OpenShockApiClient:
    """Create an API client whose User-Agent carries the installed integration version."""
    integration = await async_get_integration(hass, DOMAIN)
    return OpenShockApiClient(
        session=async_get_clientsession(hass),
        base_url=base_url,
        api_key=api_key,
        user_agent=f"{USER_AGENT_PRODUCT}/{integration.version}",
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the OpenShock integration (service actions are shared by all accounts)."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenShock from a config entry."""
    api = await async_create_api_client(hass, entry.data[CONF_BASE_URL], entry.data[CONF_API_KEY])

    poll_interval = max(
        MIN_POLL_INTERVAL,
        entry.options.get(
            CONF_POLL_INTERVAL,
            entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        ),
    )

    coordinator = OpenShockDataCoordinator(
        hass=hass,
        api=api,
        poll_interval=poll_interval,
        config_entry=entry,
    )
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_prune_stale_registry_entries()
    await coordinator.async_start_signalr()

    entry.runtime_data = {DATA_COORDINATOR: coordinator, DATA_DEFAULTS: {}}
    # Reload when the entry changes (options flow or reconfigure) so new settings apply.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry after its data or options were updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload OpenShock config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded:
        await entry.runtime_data[DATA_COORDINATOR].async_stop_signalr()

    return unloaded
