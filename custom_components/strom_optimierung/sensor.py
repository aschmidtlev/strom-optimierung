"""Sensoren der Integration strom_optimierung.

Alle Entities sind reine Anzeige- und Entscheidungswerte. Die Integration
setzt bewusst keinen Schaltbefehl am Speicher ab, solange dessen Steuer-
Entities nicht belegt verifiziert sind (siehe `docs/strom_v1_open_questions.md`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import StromOptimierungConfigEntry
from .const import ACTIONS, SOURCE_AI, SOURCE_AI_FALLBACK, SOURCE_RULE
from .coordinator import StromOptimierungCoordinator
from .entity import StromOptimierungEntity
from .optimizer import Decision


@dataclass(frozen=True, kw_only=True)
class StromSensorDescription(SensorEntityDescription):
    """Sensorbeschreibung mit Wert- und Attributfunktion."""

    value_fn: Callable[[StromOptimierungCoordinator, Decision], Any]
    attributes_fn: (
        Callable[[StromOptimierungCoordinator, Decision], dict[str, Any]] | None
    ) = None


def _decision_attributes(
    coordinator: StromOptimierungCoordinator, decision: Decision
) -> dict[str, Any]:
    return {
        "begruendung": decision.reason,
        "erlaeuterung": decision.detail,
        "quelle": decision.source,
        "ziel_soc": round(decision.target_soc, 1),
        "empfohlene_ladeleistung_w": (
            round(decision.charge_power_w) if decision.charge_power_w else None
        ),
        "fenster_start": decision.window_start,
        "fenster_ende": decision.window_end,
        "erwartete_ersparnis_ct": (
            round(decision.savings_ct, 1) if decision.savings_ct is not None else None
        ),
        "fehlende_daten": decision.missing,
        # Neueste zuerst. Speist die Karte "Letzte Entscheidungen" im
        # Dashboard, weil Logbuch und Verlaufsdiagramm nur den Zustandswert
        # zeigen und die Begründung dort verloren ginge.
        "letzte_entscheidungen": [
            record.as_dict() for record in coordinator.history
        ],
    }


def _grid_power(coordinator: StromOptimierungCoordinator) -> float | None:
    data = coordinator.last_input
    if data is None or data.grid_power_w is None:
        return None
    return round(data.grid_power_w)


SENSORS: tuple[StromSensorDescription, ...] = (
    StromSensorDescription(
        key="empfehlung",
        device_class=SensorDeviceClass.ENUM,
        options=list(ACTIONS),
        value_fn=lambda _, decision: decision.action,
        attributes_fn=_decision_attributes,
    ),
    StromSensorDescription(
        key="ziel_soc",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda _, decision: round(decision.target_soc, 1),
    ),
    StromSensorDescription(
        key="empfohlene_ladeleistung",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda _, decision: (
            round(decision.charge_power_w) if decision.charge_power_w else 0
        ),
    ),
    StromSensorDescription(
        # Fasst die einzeln konfigurierten Phasen zu einem Wert zusammen.
        # Nötig, weil Flow-Karten eine einzelne Netzleistungs-Entity erwarten,
        # der Shelly Pro 3EM aber drei getrennte Phasensensoren liefert.
        key="netzleistung",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda coordinator, _: _grid_power(coordinator),
    ),
    StromSensorDescription(
        key="pv_ueberschuss",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda _, decision: (
            round(decision.surplus_w) if decision.surplus_w is not None else None
        ),
    ),
    StromSensorDescription(
        key="erwarteter_grossverbrauch",
        # Bewusst ohne device_class: SensorDeviceClass.ENERGY verlangt eine
        # zählende state_class, dies ist aber ein Prognosewert.
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda _, decision: round(decision.expected_load_kwh, 2),
    ),
    StromSensorDescription(
        key="erwartete_ersparnis",
        native_unit_of_measurement="ct",
        suggested_display_precision=0,
        value_fn=lambda _, decision: (
            round(decision.savings_ct, 1) if decision.savings_ct is not None else None
        ),
    ),
    StromSensorDescription(
        key="ladefenster_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _, decision: decision.window_start,
    ),
    StromSensorDescription(
        key="ladefenster_ende",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _, decision: decision.window_end,
    ),
    StromSensorDescription(
        key="entscheidungsquelle",
        device_class=SensorDeviceClass.ENUM,
        options=[SOURCE_RULE, SOURCE_AI, SOURCE_AI_FALLBACK],
        value_fn=lambda _, decision: decision.source,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StromOptimierungConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        StromOptimierungSensor(coordinator, description) for description in SENSORS
    )


class StromOptimierungSensor(StromOptimierungEntity, SensorEntity):
    """Ein einzelner Entscheidungswert."""

    entity_description: StromSensorDescription

    def __init__(
        self,
        coordinator: StromOptimierungCoordinator,
        description: StromSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator, self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(
            self.coordinator, self.coordinator.data
        )
