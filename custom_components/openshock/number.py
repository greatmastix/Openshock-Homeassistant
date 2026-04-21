"""Number platform for OpenShock per-shocker defaults."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ATTR_DURATION_MS, ATTR_INTENSITY, DATA_COORDINATOR, DATA_DEFAULTS, DEFAULT_DURATION_MS, DEFAULT_INTENSITY
from .entity import OpenShockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data[DATA_COORDINATOR]

    entities: list[NumberEntity] = []
    for shocker in coordinator.data:
        entities.append(OpenShockIntensityNumber(entry, coordinator, shocker))
        entities.append(OpenShockDurationNumber(entry, coordinator, shocker))

    async_add_entities(entities)


class _OpenShockBaseNumber(OpenShockEntity, NumberEntity):
    def __init__(self, entry: ConfigEntry, coordinator, shocker: dict[str, Any]) -> None:
        super().__init__(coordinator, shocker)
        self._entry = entry

    @property
    def available(self) -> bool:
        return self.shocker is not None and super().available


class OpenShockIntensityNumber(_OpenShockBaseNumber):
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1

    def __init__(self, entry: ConfigEntry, coordinator, shocker: dict[str, Any]) -> None:
        super().__init__(entry, coordinator, shocker)
        base_name = shocker.get("name") or shocker.get("label") or self._shocker_id
        self._attr_name = f"{base_name} Intensity"
        self._attr_unique_id = f"{self._shocker_id}_intensity"

    @property
    def native_value(self) -> float:
        defaults = self._entry.runtime_data[DATA_DEFAULTS].setdefault(self._shocker_id, {})
        return float(defaults.get(ATTR_INTENSITY, DEFAULT_INTENSITY))

    async def async_set_native_value(self, value: float) -> None:
        defaults = self._entry.runtime_data[DATA_DEFAULTS].setdefault(self._shocker_id, {})
        defaults[ATTR_INTENSITY] = int(value)
        self.async_write_ha_state()


class OpenShockDurationNumber(_OpenShockBaseNumber):
    _attr_native_min_value = 100
    _attr_native_max_value = 30000
    _attr_native_step = 100
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS

    def __init__(self, entry: ConfigEntry, coordinator, shocker: dict[str, Any]) -> None:
        super().__init__(entry, coordinator, shocker)
        base_name = shocker.get("name") or shocker.get("label") or self._shocker_id
        self._attr_name = f"{base_name} Duration"
        self._attr_unique_id = f"{self._shocker_id}_duration"

    @property
    def native_value(self) -> float:
        defaults = self._entry.runtime_data[DATA_DEFAULTS].setdefault(self._shocker_id, {})
        return float(defaults.get(ATTR_DURATION_MS, DEFAULT_DURATION_MS))

    async def async_set_native_value(self, value: float) -> None:
        defaults = self._entry.runtime_data[DATA_DEFAULTS].setdefault(self._shocker_id, {})
        defaults[ATTR_DURATION_MS] = int(value)
        self.async_write_ha_state()
