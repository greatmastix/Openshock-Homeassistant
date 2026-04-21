"""Sensor platform for OpenShock shocker telemetry."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DATA_COORDINATOR
from .entity import OpenShockEntity

STATUS_KEYS = ("status", "state", "connectionState")
BATTERY_KEYS = ("battery", "batteryLevel", "battery_percent")
RSSI_KEYS = ("rssi", "signal", "signalStrength")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data[DATA_COORDINATOR]

    entities: list[SensorEntity] = []
    for shocker in coordinator.data:
        if _has_any(shocker, STATUS_KEYS):
            entities.append(OpenShockStatusSensor(coordinator, shocker))
        if _has_any(shocker, BATTERY_KEYS):
            entities.append(OpenShockBatterySensor(coordinator, shocker))
        if _has_any(shocker, RSSI_KEYS):
            entities.append(OpenShockRssiSensor(coordinator, shocker))

    async_add_entities(entities)


def _has_any(data: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(data.get(key) is not None for key in keys)


class _OpenShockBaseSensor(OpenShockEntity, SensorEntity):
    def __init__(self, coordinator, shocker: dict[str, Any]) -> None:
        super().__init__(coordinator, shocker)

    @property
    def available(self) -> bool:
        return self.shocker is not None and super().available


class OpenShockStatusSensor(_OpenShockBaseSensor):
    def __init__(self, coordinator, shocker: dict[str, Any]) -> None:
        super().__init__(coordinator, shocker)
        base_name = shocker.get("name") or shocker.get("label") or self._shocker_id
        self._attr_name = f"{base_name} Status"
        self._attr_unique_id = f"{self._shocker_id}_status"

    @property
    def native_value(self) -> str:
        data = self.shocker or {}
        for key in STATUS_KEYS:
            if data.get(key) is not None:
                return str(data[key])
        return "unknown"


class OpenShockBatterySensor(_OpenShockBaseSensor):
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, shocker: dict[str, Any]) -> None:
        super().__init__(coordinator, shocker)
        base_name = shocker.get("name") or shocker.get("label") or self._shocker_id
        self._attr_name = f"{base_name} Battery"
        self._attr_unique_id = f"{self._shocker_id}_battery"

    @property
    def native_value(self) -> float | None:
        data = self.shocker or {}
        for key in BATTERY_KEYS:
            value = data.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        return None


class OpenShockRssiSensor(_OpenShockBaseSensor):
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT

    def __init__(self, coordinator, shocker: dict[str, Any]) -> None:
        super().__init__(coordinator, shocker)
        base_name = shocker.get("name") or shocker.get("label") or self._shocker_id
        self._attr_name = f"{base_name} RSSI"
        self._attr_unique_id = f"{self._shocker_id}_rssi"

    @property
    def native_value(self) -> float | None:
        data = self.shocker or {}
        for key in RSSI_KEYS:
            value = data.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        return None
