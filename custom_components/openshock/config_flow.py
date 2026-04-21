"""Config flow for OpenShock."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenShockApiClient, OpenShockApiError
from .const import CONF_API_KEY, CONF_BASE_URL, CONF_POLL_INTERVAL, DEFAULT_BASE_URL, DEFAULT_POLL_INTERVAL, DOMAIN


class OpenShockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an OpenShock config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(f"openshock::{user_input[CONF_BASE_URL]}")
            self._abort_if_unique_id_configured()

            api = OpenShockApiClient(
                session=async_get_clientsession(self.hass),
                base_url=user_input[CONF_BASE_URL],
                api_key=user_input[CONF_API_KEY],
            )
            try:
                await api.test_connection()
            except OpenShockApiError as err:
                if err.status in (401, 403):
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="OpenShock", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=5, max=300),
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OpenShockOptionsFlow:
        """Return the options flow for this handler."""
        return OpenShockOptionsFlow(config_entry)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_user(user_input)


class OpenShockOptionsFlow(config_entries.OptionsFlow):
    """OpenShock options flow for polling interval."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=self._config_entry.options.get(
                        CONF_POLL_INTERVAL,
                        self._config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300))
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

