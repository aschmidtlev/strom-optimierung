"""Konfigurationsdialog der Integration strom_optimierung.

Die Vorbelegungen entsprechen den Entities, die im CSV-Snapshot der Zielanlage
nachweislich belegt waren. Sie sind Vorschläge, keine feste Annahme: jede
Auswahl lässt sich im Dialog ändern.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AI_ENABLED,
    CONF_AI_TASK_ENTITY,
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_SOC,
    CONF_CHEAP_PERIODS,
    CONF_CYCLE_COST,
    CONF_DHW_ENERGY,
    CONF_DHW_PLANNED_START,
    CONF_EXPENSIVE_PERIODS,
    CONF_GRID_POWER,
    CONF_HOUSE_POWER,
    CONF_LOAD_POWER_ENTITIES,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_SOC,
    CONF_MIN_SOC,
    CONF_PRICE_AVG_24H,
    CONF_PRICE_MAX_TODAY,
    CONF_PRICE_MIN_TODAY,
    CONF_PRICE_NOW,
    CONF_PV_POWER,
    CONF_PV_REMAINING_TODAY,
    CONF_PV_RESERVE,
    CONF_PV_RESERVE_THRESHOLD,
    CONF_PV_TOMORROW,
    CONF_ROUND_TRIP_EFFICIENCY,
    CONF_SURPLUS_THRESHOLD,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_CYCLE_COST,
    DEFAULT_DHW_ENERGY,
    DEFAULT_MAX_CHARGE_POWER,
    DEFAULT_MAX_SOC,
    DEFAULT_MIN_SOC,
    DEFAULT_PV_RESERVE_THRESHOLD,
    DEFAULT_ROUND_TRIP_EFFICIENCY,
    DEFAULT_SURPLUS_THRESHOLD,
    DOMAIN,
)

TITLE = "Strom-Optimierung"

# Vorschlagswerte aus dem Entity-Snapshot der Zielanlage vom 08.09.2026
# (Ordner `csv/`). Jede ID ist dort belegt und war nicht `unavailable`; die
# Quellzeilen stehen in `docs/strom_v1_entity_mapping.md`. Wählt der Anwender
# im Dialog etwas anderes, gilt seine Auswahl.
SUGGESTED: dict[str, Any] = {
    CONF_PRICE_NOW: "sensor.home_aktueller_strompreis",
    CONF_CHEAP_PERIODS: "binary_sensor.home_bestpreis_zeitraum",
    CONF_EXPENSIVE_PERIODS: "binary_sensor.home_spitzenpreis_zeitraum",
    CONF_PRICE_AVG_24H: "sensor.home_preis_vorlaufend_24h",
    CONF_PRICE_MIN_TODAY: "sensor.home_mindestpreis_heute",
    CONF_PRICE_MAX_TODAY: "sensor.home_hochstpreis_heute",
    CONF_PV_REMAINING_TODAY: [
        "sensor.energy_production_today_remaining",
        "sensor.energy_production_today_remaining_2",
    ],
    CONF_PV_TOMORROW: [
        "sensor.energy_production_tomorrow",
        "sensor.energy_production_tomorrow_2",
    ],
    CONF_PV_POWER: "sensor.stp10_0_3av_40_040_pv_power",
    CONF_GRID_POWER: [
        "sensor.shellypro3em_ecc9ffe7c9dc_phase_a_leistung",
        "sensor.shellypro3em_ecc9ffe7c9dc_phase_b_leistung",
        "sensor.shellypro3em_ecc9ffe7c9dc_phase_c_leistung",
    ],
    CONF_HOUSE_POWER: "sensor.ww_v3_hausverbrauch_berechnet",
    # Der Marstek-SoC war im Snapshot `unavailable`; er wird deshalb bewusst
    # nicht vorgeschlagen und muss vom Anwender ausgewählt werden, sobald die
    # Modbus-Verbindung wieder steht.
    CONF_DHW_PLANNED_START: "sensor.ww_v3_naechster_bestpreis_start",
    CONF_LOAD_POWER_ENTITIES: [
        "sensor.waschmaschine_energy_power",
        "sensor.trockner_aktuelle_leistung",
        "sensor.spuehlmaschine_energy_power",
    ],
    CONF_AI_TASK_ENTITY: "ai_task.claude_ai_task",
}


def _entity(domain: str | list[str], multiple: bool = False) -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domain, multiple=multiple)
    )


def _opt(key: str, defaults: dict[str, Any]) -> vol.Optional:
    """Optionales Feld mit Vorschlagswert statt hartem Default."""
    return vol.Optional(key, description={"suggested_value": defaults.get(key)})


def _number(
    minimum: float, maximum: float, step: float, unit: str | None = None
) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(
        min=minimum,
        max=maximum,
        step=step,
        mode=selector.NumberSelectorMode.BOX,
    )
    # `unit_of_measurement` muss weggelassen werden, wenn es keine Einheit
    # gibt: das Schema von NumberSelector prüft den Schlüssel gegen `str` und
    # weist `None` zurück. Der Wirkungsgrad ist das einzige einheitenlose Feld.
    if unit is not None:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def price_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_PRICE_NOW,
                description={"suggested_value": defaults.get(CONF_PRICE_NOW)},
            ): _entity("sensor"),
            vol.Required(
                CONF_CHEAP_PERIODS,
                description={"suggested_value": defaults.get(CONF_CHEAP_PERIODS)},
            ): _entity(["binary_sensor", "sensor"]),
            vol.Required(
                CONF_EXPENSIVE_PERIODS,
                description={"suggested_value": defaults.get(CONF_EXPENSIVE_PERIODS)},
            ): _entity(["binary_sensor", "sensor"]),
            _opt(CONF_PRICE_AVG_24H, defaults): _entity("sensor"),
            _opt(CONF_PRICE_MIN_TODAY, defaults): _entity("sensor"),
            _opt(CONF_PRICE_MAX_TODAY, defaults): _entity("sensor"),
        }
    )


def pv_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            _opt(CONF_PV_REMAINING_TODAY, defaults): _entity("sensor", multiple=True),
            _opt(CONF_PV_TOMORROW, defaults): _entity("sensor", multiple=True),
            _opt(CONF_PV_POWER, defaults): _entity("sensor"),
            _opt(CONF_GRID_POWER, defaults): _entity("sensor", multiple=True),
            _opt(CONF_HOUSE_POWER, defaults): _entity("sensor"),
        }
    )


def battery_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            _opt(CONF_BATTERY_SOC, defaults): _entity("sensor"),
            vol.Required(
                CONF_BATTERY_CAPACITY,
                default=defaults.get(CONF_BATTERY_CAPACITY, DEFAULT_BATTERY_CAPACITY),
            ): _number(0.5, 100, 0.01, "kWh"),
            vol.Required(
                CONF_ROUND_TRIP_EFFICIENCY,
                default=defaults.get(
                    CONF_ROUND_TRIP_EFFICIENCY, DEFAULT_ROUND_TRIP_EFFICIENCY
                ),
            ): _number(0.5, 1.0, 0.01),
            vol.Required(
                CONF_CYCLE_COST,
                default=defaults.get(CONF_CYCLE_COST, DEFAULT_CYCLE_COST),
            ): _number(0, 20, 0.1, "ct/kWh"),
            vol.Required(
                CONF_MIN_SOC, default=defaults.get(CONF_MIN_SOC, DEFAULT_MIN_SOC)
            ): _number(0, 100, 1, "%"),
            vol.Required(
                CONF_MAX_SOC, default=defaults.get(CONF_MAX_SOC, DEFAULT_MAX_SOC)
            ): _number(0, 100, 1, "%"),
            vol.Required(
                CONF_MAX_CHARGE_POWER,
                default=defaults.get(CONF_MAX_CHARGE_POWER, DEFAULT_MAX_CHARGE_POWER),
            ): _number(100, 20000, 50, "W"),
            vol.Required(
                CONF_SURPLUS_THRESHOLD,
                default=defaults.get(
                    CONF_SURPLUS_THRESHOLD, DEFAULT_SURPLUS_THRESHOLD
                ),
            ): _number(0, 5000, 10, "W"),
            vol.Required(
                CONF_PV_RESERVE, default=defaults.get(CONF_PV_RESERVE, True)
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_PV_RESERVE_THRESHOLD,
                default=defaults.get(
                    CONF_PV_RESERVE_THRESHOLD, DEFAULT_PV_RESERVE_THRESHOLD
                ),
            ): _number(0, 100, 0.5, "kWh"),
        }
    )


def loads_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            _opt(CONF_DHW_PLANNED_START, defaults): _entity("sensor"),
            vol.Required(
                CONF_DHW_ENERGY,
                default=defaults.get(CONF_DHW_ENERGY, DEFAULT_DHW_ENERGY),
            ): _number(0.1, 50, 0.1, "kWh"),
            _opt(CONF_LOAD_POWER_ENTITIES, defaults): _entity(
                "sensor", multiple=True
            ),
            vol.Required(
                CONF_AI_ENABLED, default=defaults.get(CONF_AI_ENABLED, False)
            ): selector.BooleanSelector(),
            _opt(CONF_AI_TASK_ENTITY, defaults): _entity("ai_task"),
        }
    )


def _strip_empty(user_input: dict[str, Any]) -> dict[str, Any]:
    """Entfernt leere Auswahlfelder, damit sie als 'nicht gesetzt' gelten."""
    return {
        key: value
        for key, value in user_input.items()
        if value not in (None, "", [])
    }


class StromOptimierungConfigFlow(ConfigFlow, domain=DOMAIN):
    """Vierstufiger Einrichtungsdialog."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(_strip_empty(user_input))
            return await self.async_step_pv()
        return self.async_show_form(step_id="user", data_schema=price_schema(SUGGESTED))

    async def async_step_pv(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(_strip_empty(user_input))
            return await self.async_step_battery()
        return self.async_show_form(step_id="pv", data_schema=pv_schema(SUGGESTED))

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input[CONF_MIN_SOC] >= user_input[CONF_MAX_SOC]:
                return self.async_show_form(
                    step_id="battery",
                    data_schema=battery_schema(user_input),
                    errors={"base": "soc_range"},
                )
            self._data.update(_strip_empty(user_input))
            return await self.async_step_loads()
        return self.async_show_form(step_id="battery", data_schema=battery_schema(SUGGESTED))

    async def async_step_loads(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input.get(CONF_AI_ENABLED) and not user_input.get(
                CONF_AI_TASK_ENTITY
            ):
                return self.async_show_form(
                    step_id="loads",
                    data_schema=loads_schema(user_input),
                    errors={"base": "ai_entity_missing"},
                )
            self._data.update(_strip_empty(user_input))
            self._data[CONF_AI_ENABLED] = bool(user_input.get(CONF_AI_ENABLED))
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=TITLE, data=self._data)
        return self.async_show_form(step_id="loads", data_schema=loads_schema(SUGGESTED))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return StromOptimierungOptionsFlow()


class StromOptimierungOptionsFlow(OptionsFlow):
    """Nachträgliche Anpassung aller Quellen und Parameter.

    Bewusst als Menü über dieselben vier Bereiche wie die Einrichtung: sonst
    liessen sich nach dem ersten Speichern weder die Quell-Entities noch der
    KI-Pfad je wieder ändern.
    """

    @property
    def _current(self) -> dict[str, Any]:
        return {**self.config_entry.data, **self.config_entry.options}

    def _save(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(
            data={**self._current, **_strip_empty(user_input)}
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["preise", "pv", "speicher", "lasten"],
        )

    async def async_step_preise(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input)
        return self.async_show_form(
            step_id="preise", data_schema=price_schema(self._current)
        )

    async def async_step_pv(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input)
        return self.async_show_form(
            step_id="pv", data_schema=pv_schema(self._current)
        )

    async def async_step_speicher(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input[CONF_MIN_SOC] >= user_input[CONF_MAX_SOC]:
                return self.async_show_form(
                    step_id="speicher",
                    data_schema=battery_schema({**self._current, **user_input}),
                    errors={"base": "soc_range"},
                )
            return self._save(user_input)
        return self.async_show_form(
            step_id="speicher", data_schema=battery_schema(self._current)
        )

    async def async_step_lasten(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input.get(CONF_AI_ENABLED) and not user_input.get(
                CONF_AI_TASK_ENTITY
            ):
                return self.async_show_form(
                    step_id="lasten",
                    data_schema=loads_schema({**self._current, **user_input}),
                    errors={"base": "ai_entity_missing"},
                )
            return self._save(user_input)
        return self.async_show_form(
            step_id="lasten", data_schema=loads_schema(self._current)
        )
