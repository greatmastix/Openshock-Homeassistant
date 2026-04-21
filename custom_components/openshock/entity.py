"""Shared OpenShock entity helpers."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenShockDataCoordinator


class OpenShockEntity(CoordinatorEntity[OpenShockDataCoordinator]):
    """Base OpenShock entity."""

    def __init__(self, coordinator: OpenShockDataCoordinator, shocker: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._shocker_id = str(
            shocker.get("id")
            or shocker.get("shockerId")
            or shocker.get("shocker_id")
            or shocker.get("uuid")
        )

    @property
    def shocker(self) -> dict[str, Any] | None:
        for item in self.coordinator.data:
            item_id = str(item.get("id") or item.get("shockerId") or item.get("shocker_id") or item.get("uuid"))
            if item_id == self._shocker_id:
                return item
        return None

    @property
    def device_info(self) -> DeviceInfo:
        data = self.shocker or {}
        name = (
            data.get("name")
            or data.get("label")
            or data.get("deviceName")
            or f"Shocker {self._shocker_id}"
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self._shocker_id)},
            name=name,
            manufacturer="OpenShock",
            model=data.get("model") or "Shocker",
        )
