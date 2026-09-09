"""Schalter der Integration strom_optimierung.

Der einzige Schalter steuert den optionalen KI-Pfad. Er wirkt ausschliesslich
innerhalb dieser Integration und sendet keinen Befehl an ein Gerät – passend
dazu, dass die Integration den Speicher bewusst nicht ansteuert.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import StromOptimierungConfigEntry
from .const import CONF_AI_TASK_ENTITY
from .coordinator import StromOptimierungCoordinator
from .entity import StromOptimierungEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StromOptimierungConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([StromOptimierungAiSwitch(entry.runtime_data)])


class StromOptimierungAiSwitch(
    StromOptimierungEntity, SwitchEntity, RestoreEntity
):
    """Schaltet die KI-Verfeinerung der Entscheidung ein und aus.

    Der Zustand wird über einen Neustart hinweg wiederhergestellt und nicht in
    die Konfiguration zurückgeschrieben. Ein Schreiben in die Optionen würde
    die Integration bei jedem Umschalten neu laden und dabei alle Entities
    kurzzeitig verschwinden lassen.
    """

    def __init__(self, coordinator: StromOptimierungCoordinator) -> None:
        super().__init__(coordinator, "ki_entscheidung_nutzen")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self.coordinator.ai_enabled = last_state.state == "on"

    @property
    def is_on(self) -> bool:
        return self.coordinator.ai_enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Macht sichtbar, warum der Schalter gegebenenfalls wirkungslos ist."""
        entity_id = self.coordinator.entry.options.get(
            CONF_AI_TASK_ENTITY,
            self.coordinator.entry.data.get(CONF_AI_TASK_ENTITY),
        )
        return {
            "ai_task_entity": entity_id,
            "wirksam": bool(entity_id),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, enabled: bool) -> None:
        self.coordinator.ai_enabled = enabled
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
