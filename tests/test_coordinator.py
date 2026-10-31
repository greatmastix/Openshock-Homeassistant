"""Tests for removing the devices and entities of deleted shockers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.openshock.const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    DATA_COORDINATOR,
    DEFAULT_BASE_URL,
    DOMAIN,
)

DEPRECATION_WARNING = "Detected that custom integration 'openshock'"


def _shocker(shocker_id: str) -> dict[str, Any]:
    return {"id": shocker_id, "name": f"Shocker {shocker_id}"}


@pytest.fixture
def shockers() -> list[dict[str, Any]]:
    """Shockers the mocked OpenShock account currently lists."""
    return [_shocker("keep"), _shocker("delete")]


@pytest.fixture(autouse=True)
async def mock_openshock(shockers: list[dict[str, Any]]) -> AsyncGenerator[None]:
    """Mock the OpenShock API and SignalR hub."""
    with (
        patch(
            "custom_components.openshock.api.OpenShockApiClient.get_shockers",
            new=AsyncMock(side_effect=lambda: list(shockers)),
        ),
        patch(
            "custom_components.openshock.signalr.OpenShockSignalRClient.run",
            new=AsyncMock(),
        ),
    ):
        yield


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add an OpenShock config entry to Home Assistant."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"openshock::{DEFAULT_BASE_URL}",
        data={CONF_BASE_URL: DEFAULT_BASE_URL, CONF_API_KEY: "token"},
    )
    entry.add_to_hass(hass)
    return entry


def _device_for_shocker(hass: HomeAssistant, entry: MockConfigEntry, shocker_id: str) -> dr.DeviceEntry:
    """Return the entry's device of a shocker (works on old and new device registries)."""
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    return next(device for device in devices if (DOMAIN, shocker_id) in device.identifiers)


def _device_ids(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    """Return the shocker ids of the devices that belong to the entry."""
    return {
        identifier
        for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
        for domain, identifier in device.identifiers
        if domain == DOMAIN
    }


def _entity_unique_ids(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    return {
        entity.unique_id
        for entity in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }


async def test_refresh_removes_deleted_shocker(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    shockers: list[dict[str, Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A shocker deleted from the account loses its device and entities on refresh."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert _device_ids(hass, config_entry) == {"keep", "delete"}
    assert any(uid.startswith("delete_") for uid in _entity_unique_ids(hass, config_entry))

    shockers.remove(_shocker("delete"))
    await config_entry.runtime_data[DATA_COORDINATOR].async_refresh()
    await hass.async_block_till_done()

    assert _device_ids(hass, config_entry) == {"keep"}
    unique_ids = _entity_unique_ids(hass, config_entry)
    assert unique_ids
    assert all(uid.startswith("keep_") for uid in unique_ids)
    assert DEPRECATION_WARNING not in caplog.text


async def test_refresh_removes_other_entities_of_deleted_device(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    shockers: list[dict[str, Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Entities left on a deleted shocker's device are removed with the device."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    device = _device_for_shocker(hass, config_entry, "delete")
    # Its unique id does not start with the shocker id, so only the device removal
    # can clean it up.
    entity_registry = er.async_get(hass)
    other_entity = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "unrelated",
        config_entry=config_entry,
        device_id=device.id,
    )

    shockers.remove(_shocker("delete"))
    await config_entry.runtime_data[DATA_COORDINATOR].async_refresh()
    await hass.async_block_till_done()

    assert device_registry.async_get(device.id) is None
    assert entity_registry.async_get(other_entity.entity_id) is None
    assert _device_ids(hass, config_entry) == {"keep"}
    assert DEPRECATION_WARNING not in caplog.text


async def test_setup_prunes_stale_devices(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Devices of shockers deleted while Home Assistant was stopped are pruned on setup."""
    device_registry = dr.async_get(hass)
    stale_device = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "stale")},
        name="Shocker stale",
    )
    entity_registry = er.async_get(hass)
    stale_entity = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "stale_status",
        config_entry=config_entry,
        device_id=stale_device.id,
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert device_registry.async_get(stale_device.id) is None
    assert entity_registry.async_get(stale_entity.entity_id) is None
    assert _device_ids(hass, config_entry) == {"keep", "delete"}
    assert DEPRECATION_WARNING not in caplog.text
