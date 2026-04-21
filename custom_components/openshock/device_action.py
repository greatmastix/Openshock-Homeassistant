"""Device actions for OpenShock."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.const import ATTR_DEVICE_ID, CONF_DOMAIN, CONF_TYPE
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    ATTR_COMMAND,
    ATTR_DURATION_MS,
    ATTR_INTENSITY,
    ATTR_SHOCKER_ID,
    COMMAND_SHOCK,
    COMMAND_SOUND,
    COMMAND_VIBRATE,
    DEFAULT_DURATION_MS,
    DEFAULT_INTENSITY,
    DOMAIN,
    SERVICE_SEND_COMMAND,
)

ACTION_SHOCK = "shock"
ACTION_BEEP = "beep"
ACTION_VIBRATE = "vibrate"

ACTIONS = (ACTION_SHOCK, ACTION_BEEP, ACTION_VIBRATE)
ACTION_TO_COMMAND = {
    ACTION_SHOCK: COMMAND_SHOCK,
    ACTION_BEEP: COMMAND_SOUND,
    ACTION_VIBRATE: COMMAND_VIBRATE,
}

ACTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DOMAIN): DOMAIN,
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(CONF_TYPE): vol.In(ACTIONS),
        vol.Optional(ATTR_INTENSITY, default=DEFAULT_INTENSITY): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        ),
        vol.Optional(ATTR_DURATION_MS, default=DEFAULT_DURATION_MS): vol.All(
            vol.Coerce(int), vol.Range(min=100, max=30000)
        ),
    }
)


def _async_get_shocker_id(hass: HomeAssistant, device_id: str) -> str | None:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None

    for identifier_domain, identifier_id in device.identifiers:
        if identifier_domain == DOMAIN:
            return identifier_id

    return None


async def async_get_actions(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    """List device actions for OpenShock devices."""
    if _async_get_shocker_id(hass, device_id) is None:
        return []

    return [
        {
            CONF_DOMAIN: DOMAIN,
            ATTR_DEVICE_ID: device_id,
            CONF_TYPE: action,
        }
        for action in ACTIONS
    ]


async def async_validate_action_config(hass: HomeAssistant, config: dict[str, Any]) -> dict[str, Any]:
    """Validate an OpenShock action config."""
    return ACTION_SCHEMA(config)


async def async_call_action_from_config(
    hass: HomeAssistant,
    config: dict[str, Any],
    variables: dict[str, Any],
    context: Context | None,
) -> None:
    """Execute an OpenShock device action."""
    config = ACTION_SCHEMA(config)
    shocker_id = _async_get_shocker_id(hass, config[ATTR_DEVICE_ID])

    if shocker_id is None:
        return

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        {
            ATTR_SHOCKER_ID: shocker_id,
            ATTR_COMMAND: ACTION_TO_COMMAND[config[CONF_TYPE]],
            ATTR_INTENSITY: config[ATTR_INTENSITY],
            ATTR_DURATION_MS: config[ATTR_DURATION_MS],
        },
        blocking=True,
        context=context,
    )


async def async_get_action_capabilities(
    hass: HomeAssistant,
    config: dict[str, Any],
) -> dict[str, vol.Schema]:
    """List extra fields for OpenShock device actions."""
    return {
        "extra_fields": vol.Schema(
            {
                vol.Optional(ATTR_INTENSITY, default=DEFAULT_INTENSITY): NumberSelector(
                    NumberSelectorConfig(min=1, max=100, step=1, mode=NumberSelectorMode.SLIDER)
                ),
                vol.Optional(ATTR_DURATION_MS, default=DEFAULT_DURATION_MS): NumberSelector(
                    NumberSelectorConfig(min=100, max=30000, step=100, mode=NumberSelectorMode.BOX)
                ),
            }
        )
    }
