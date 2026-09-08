"""Binärsensoren der Integration strom_optimierung."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import StromOptimierungConfigEntry
from .const import ACTION_CHARGE_ANTICIPATORY, ACTION_CHARGE_PRICE, ACTION_CHARGE_PV
from .coordinator import StromOptimierungCoordinator
from .entity import StromOptimierungEntity
from .optimizer import Decision, current_period

CHARGING_ACTIONS = {ACTION_CHARGE_PV, ACTION_CHARGE_PRICE, ACTION_CHARGE_ANTICIPATORY}


@dataclass(frozen=True, kw_only=True)
class StromBinarySensorDescription(BinarySensorEntityDescription):
    """Binärsensor mit eigener Auswertefunktion."""

    value_fn: Callable[[StromOptimierungCoordinator, Decision], bool]


def _cheap_window_active(
    coordinator: StromOptimierungCoordinator, decision: Decision
) -> bool:
    data = coordinator.last_input
    if data is None:
        return False
    return current_period(data.cheap_periods, data.now) is not None


BINARY_SENSORS: tuple[StromBinarySensorDescription, ...] = (
    StromBinarySensorDescription(
        key="laden_empfohlen",
        value_fn=lambda _, decision: decision.action in CHARGING_ACTIONS,
    ),
    StromBinarySensorDescription(
        key="guenstiges_fenster_aktiv",
        value_fn=_cheap_window_active,
    ),
    StromBinarySensorDescription(
        key="datenbasis_unvollstaendig",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda _, decision: bool(decision.missing),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StromOptimierungConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        StromOptimierungBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class StromOptimierungBinarySensor(StromOptimierungEntity, BinarySensorEntity):
    """Ein einzelner Zustandsindikator."""

    entity_description: StromBinarySensorDescription

    def __init__(
        self,
        coordinator: StromOptimierungCoordinator,
        description: StromBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator, self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, list[str]] | None:
        if self.entity_description.key != "datenbasis_unvollstaendig":
            return None
        return {"fehlende_daten": self.coordinator.data.missing}
