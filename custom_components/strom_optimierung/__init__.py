"""Integration strom_optimierung: Ladeempfehlung für einen Hausbatteriespeicher."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import StromOptimierungCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type StromOptimierungConfigEntry = ConfigEntry[StromOptimierungCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: StromOptimierungConfigEntry
) -> bool:
    coordinator = StromOptimierungCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: StromOptimierungConfigEntry
) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant, entry: StromOptimierungConfigEntry
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
