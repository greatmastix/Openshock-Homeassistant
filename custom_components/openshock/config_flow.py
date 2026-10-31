"""Config flow for OpenShock."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from . import async_create_api_client
from .api import AUTH_ERROR_STATUSES, OpenShockApiError
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_POLL_INTERVAL,
    DEFAULT_BASE_URL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MIN_POLL_INTERVAL,
)


class OpenShockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an OpenShock config flow."""

    VERSION = 1

    async def _async_validate_input(self, base_url: str, api_key: str) -> dict[str, str]:
        """Try the credentials against the API and return form errors, if any."""
        api = await async_create_api_client(self.hass, base_url, api_key)
        try:
            await api.test_connection()
        except OpenShockApiError as err:
            if err.status in AUTH_ERROR_STATUSES:
                return {"base": "invalid_auth"}
            return {"base": "cannot_connect"}
        return {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(f"openshock::{user_input[CONF_BASE_URL]}")
            self._abort_if_unique_id_configured()

            errors = await self._async_validate_input(user_input[CONF_BASE_URL], user_input[CONF_API_KEY])
            if not errors:
                return self.async_create_entry(title="OpenShock", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_POLL_INTERVAL, max=86400),
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OpenShockOptionsFlow:
        """Return the options flow for this handler."""
        return OpenShockOptionsFlow(config_entry)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the API URL or token of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL]
            # An empty token field keeps the current token.
            api_key = user_input.get(CONF_API_KEY) or entry.data[CONF_API_KEY]
            unique_id = f"openshock::{base_url}"

            if any(
                other.entry_id != entry.entry_id and other.unique_id == unique_id
                for other in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")

            errors = await self._async_validate_input(base_url, api_key)
            if not errors:
                # The update listener in __init__.py reloads the entry with the new data.
                self.hass.config_entries.async_update_entry(
                    entry,
                    unique_id=unique_id,
                    data={**entry.data, CONF_BASE_URL: base_url, CONF_API_KEY: api_key},
                )
                return self.async_abort(reason="reconfigure_successful")

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=entry.data[CONF_BASE_URL]): str,
                vol.Optional(CONF_API_KEY): str,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)


class OpenShockOptionsFlow(config_entries.OptionsFlow):
    """OpenShock options flow for polling interval."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        configured_poll_interval = self._config_entry.options.get(
            CONF_POLL_INTERVAL,
            self._config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        )
        default_poll_interval = max(MIN_POLL_INTERVAL, configured_poll_interval)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=default_poll_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL, max=86400))
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

