"""Button platform for OpenShock controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import OpenShockApiError
from .const import (
    ATTR_DURATION_MS,
    ATTR_INTENSITY,
    COMMAND_SHOCK,
    COMMAND_SOUND,
    COMMAND_STOP,
    COMMAND_VIBRATE,
    DATA_COORDINATOR,
    DATA_DEFAULTS,
    DEFAULT_DURATION_MS,
    DEFAULT_INTENSITY,
)
from .entity import OpenShockEntity


@dataclass(frozen=True, kw_only=True)
class OpenShockButtonDescription(ButtonEntityDescription):
    """Describes an OpenShock command button."""

    command: str


BUTTONS: tuple[OpenShockButtonDescription, ...] = (
    OpenShockButtonDescription(key="shock", name="Shock", command=COMMAND_SHOCK),
    OpenShockButtonDescription(key="vibrate", name="Vibrate", command=COMMAND_VIBRATE),
    OpenShockButtonDescription(key="sound", name="Sound", command=COMMAND_SOUND),
    OpenShockButtonDescription(key="stop", name="Stop", command=COMMAND_STOP),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data[DATA_COORDINATOR]
    known_ids: set[str] = set()

    def shocker_id(shocker: dict[str, Any]) -> str | None:
        value = shocker.get("id") or shocker.get("shockerId") or shocker.get("shocker_id") or shocker.get("uuid")
        return str(value) if value else None

    def build_new_entities() -> list[OpenShockCommandButton]:
        entities: list[OpenShockCommandButton] = []
        for shocker in coordinator.data:
            current_id = shocker_id(shocker)
            if not current_id or current_id in known_ids:
                continue
            known_ids.add(current_id)
            for description in BUTTONS:
                entities.append(OpenShockCommandButton(entry, coordinator, shocker, description))
        return entities

    async_add_entities(build_new_entities())

    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: async_add_entities(build_new_entities()),
        )
    )


class OpenShockCommandButton(OpenShockEntity, ButtonEntity):
    """Button entity for a single OpenShock command."""

    entity_description: OpenShockButtonDescription

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator,
        shocker: dict[str, Any],
        description: OpenShockButtonDescription,
    ) -> None:
        super().__init__(coordinator, shocker)
        self._entry = entry
        self.entity_description = description

        base_name = shocker.get("name") or shocker.get("label") or self._shocker_id
        self._attr_name = f"{base_name} {description.name}"
        self._attr_unique_id = f"{self._shocker_id}_{description.key}"

    @property
    def available(self) -> bool:
        return self.shocker is not None and super().available

    async def async_press(self) -> None:
        defaults = self._entry.runtime_data[DATA_DEFAULTS].get(self._shocker_id, {})

        intensity = defaults.get(ATTR_INTENSITY, DEFAULT_INTENSITY)
        duration_ms = defaults.get(ATTR_DURATION_MS, DEFAULT_DURATION_MS)
        if self.entity_description.command == COMMAND_STOP:
            intensity = None
            duration_ms = None

        try:
            await self.coordinator.api.send_command(
                shocker_id=self._shocker_id,
                command=self.entity_description.command,
                intensity=intensity,
                duration_ms=duration_ms,
            )
            await self.coordinator.async_request_refresh()
        except OpenShockApiError as err:
            raise HomeAssistantError(str(err)) from err
