"""Gemeinsame Basis der Entities dieser Integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import StromOptimierungCoordinator


class StromOptimierungEntity(CoordinatorEntity[StromOptimierungCoordinator]):
    """Bindet alle Entities an ein gemeinsames Dienstgerät."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: StromOptimierungCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Strom-Optimierung",
            manufacturer="aschmidtlev",
            entry_type=DeviceEntryType.SERVICE,
        )
