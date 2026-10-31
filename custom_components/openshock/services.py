"""Service actions for the OpenShock integration."""

from __future__ import annotations

import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .api import OpenShockApiError
from .const import (
    ATTR_COMMAND,
    ATTR_DURATION_MS,
    ATTR_INTENSITY,
    ATTR_SHOCKER_ID,
    COMMAND_STOP,
    DATA_COORDINATOR,
    DATA_DEFAULTS,
    DEFAULT_DURATION_MS,
    DEFAULT_INTENSITY,
    DOMAIN,
    SERVICE_SEND_COMMAND,
    SERVICE_STOP_ALL,
    VALID_COMMANDS,
)

SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_SHOCKER_ID): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
        vol.Required(ATTR_COMMAND): vol.In(VALID_COMMANDS),
        vol.Optional(ATTR_INTENSITY): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional(ATTR_DURATION_MS): vol.All(vol.Coerce(int), vol.Range(min=100, max=30000)),
    }
)


def _loaded_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("No OpenShock account is loaded")
    return entries


def _resolve_target(hass: HomeAssistant, call: ServiceCall) -> tuple[ConfigEntry, str]:
    """Return the config entry (account) and shocker id a send_command call targets."""
    entries = _loaded_entries(hass)

    shocker_id: str | None = call.data.get(ATTR_SHOCKER_ID)
    device_entry_ids: set[str] = set()
    if (device_id := call.data.get(CONF_DEVICE_ID)) is not None and (
        device := dr.async_get(hass).async_get(device_id)
    ) is not None:
        # HA 2026.x gives a device a single `config_entry_id`; older versions use
        # the (now deprecated) `config_entries` set.
        if (owner_entry_id := getattr(device, "config_entry_id", None)) is not None:
            device_entry_ids = {owner_entry_id}
        else:
            device_entry_ids = set(device.config_entries)
        if shocker_id is None:
            shocker_id = next(
                (identifier for domain, identifier in device.identifiers if domain == DOMAIN),
                None,
            )

    if shocker_id is None:
        raise ServiceValidationError("Provide shocker_id or device_id for openshock.send_command")

    # Prefer the account that owns the device, then the account that lists the shocker.
    for entry in entries:
        if entry.entry_id in device_entry_ids:
            return entry, shocker_id
    for entry in entries:
        if entry.runtime_data[DATA_COORDINATOR].has_shocker(shocker_id):
            return entry, shocker_id

    # The shocker is not listed by any account (e.g. it is shared with the user).
    # That is only unambiguous when a single account is configured.
    if len(entries) == 1:
        return entries[0], shocker_id

    raise ServiceValidationError(
        f"Shocker {shocker_id} does not belong to any loaded OpenShock account"
    )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register OpenShock service actions."""

    async def async_send_command(call: ServiceCall) -> None:
        entry, shocker_id = _resolve_target(hass, call)
        command = call.data[ATTR_COMMAND]

        defaults = entry.runtime_data[DATA_DEFAULTS].get(shocker_id, {})
        intensity = call.data.get(ATTR_INTENSITY, defaults.get(ATTR_INTENSITY, DEFAULT_INTENSITY))
        duration_ms = call.data.get(ATTR_DURATION_MS, defaults.get(ATTR_DURATION_MS, DEFAULT_DURATION_MS))

        if command == COMMAND_STOP:
            intensity = None
            duration_ms = None

        try:
            await entry.runtime_data[DATA_COORDINATOR].api.send_command(
                shocker_id=shocker_id,
                command=command,
                intensity=intensity,
                duration_ms=duration_ms,
            )
        except OpenShockApiError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_stop_all(_: ServiceCall) -> None:
        # Stop every account, even if one of them fails.
        entries = _loaded_entries(hass)
        results = await asyncio.gather(
            *(entry.runtime_data[DATA_COORDINATOR].api.stop_all() for entry in entries),
            return_exceptions=True,
        )
        errors: list[str] = []
        for result in results:
            if isinstance(result, OpenShockApiError):
                errors.append(str(result))
            elif isinstance(result, BaseException):
                raise result
        if errors:
            raise HomeAssistantError("; ".join(errors))

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        async_send_command,
        schema=SEND_COMMAND_SCHEMA,
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP_ALL, async_stop_all)
