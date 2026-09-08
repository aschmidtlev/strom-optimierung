"""Diagnosedaten: welche Werte die letzte Entscheidung getragen haben."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from . import StromOptimierungConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: StromOptimierungConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "config": {**entry.data, **entry.options},
        "eingang": asdict(coordinator.last_input) if coordinator.last_input else None,
        "entscheidung": asdict(coordinator.data) if coordinator.data else None,
        "historie": [record.as_dict() for record in coordinator.history],
        "aktuelle_verbraucherleistung_w": coordinator.current_load_power_w(),
    }
