"""Sammelt die Quellwerte aus Home Assistant und trifft die Entscheidung."""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .ai_advisor import AiAdvisor
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
    UPDATE_INTERVAL_SECONDS,
)
from .optimizer import Decision, ExpectedLoad, OptimizerInput, PricePeriod, decide

_LOGGER = logging.getLogger(__name__)

UNKNOWN_STATES = {"unknown", "unavailable", "none", ""}

# Wie viele zurückliegende Entscheidungen vorgehalten werden. Der Wert geht
# als Zustandsattribut in die Datenbank; deshalb bewusst klein gehalten.
MAX_HISTORY = 5


@dataclass(frozen=True)
class DecisionRecord:
    """Eine zurückliegende Entscheidung samt Begründung."""

    zeit: str
    aktion: str
    begruendung: str
    erlaeuterung: str
    ziel_soc: float
    ersparnis_ct: float | None
    quelle: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "zeit": self.zeit,
            "aktion": self.aktion,
            "begruendung": self.begruendung,
            "erlaeuterung": self.erlaeuterung,
            "ziel_soc": self.ziel_soc,
            "ersparnis_ct": self.ersparnis_ct,
            "quelle": self.quelle,
        }


class StromOptimierungCoordinator(DataUpdateCoordinator[Decision]):
    """Liest die Quell-Entities und berechnet die Ladeempfehlung."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.advisor = AiAdvisor(hass, entry)
        self.last_input: OptimizerInput | None = None
        # Neueste Entscheidung zuerst.
        self.history: deque[DecisionRecord] = deque(maxlen=MAX_HISTORY)

    # --- Zugriff auf Zustände ---------------------------------------------

    def _option(self, key: str, default: Any = None) -> Any:
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    def _state(self, entity_id: str | None) -> str | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state.lower() in UNKNOWN_STATES:
            return None
        return state.state

    def _float(self, key: str) -> float | None:
        raw = self._state(self._option(key))
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            _LOGGER.debug("Wert von %s ist nicht numerisch: %s", key, raw)
            return None

    def _float_sum(self, key: str) -> float | None:
        """Summe mehrerer Entities; None, wenn keine einzige Wert liefert."""
        entity_ids = self._option(key) or []
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        total: float | None = None
        for entity_id in entity_ids:
            raw = self._state(entity_id)
            if raw is None:
                continue
            try:
                total = (total or 0.0) + float(raw)
            except ValueError:
                _LOGGER.debug("Wert von %s ist nicht numerisch: %s", entity_id, raw)
        return total

    def _attribute(self, key: str, attribute: str) -> Any:
        entity_id = self._option(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        return state.attributes.get(attribute)

    # --- Aufbereitung ------------------------------------------------------

    def _periods(self, key: str) -> list[PricePeriod]:
        """Liest das Attribut `periods` der Tibber-Zeitraum-Sensoren."""
        raw = self._attribute(key, "periods")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                _LOGGER.warning("Attribut 'periods' von %s ist kein gültiges JSON", key)
                return []
        if not isinstance(raw, list):
            return []

        periods: list[PricePeriod] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            start = _parse_datetime(item.get("start"))
            end = _parse_datetime(item.get("end"))
            mean = _as_float(item.get("price_mean"))
            if start is None or end is None or mean is None:
                continue
            periods.append(
                PricePeriod(
                    start=start,
                    end=end,
                    price_mean=mean,
                    price_min=_as_float(item.get("price_min")),
                    price_max=_as_float(item.get("price_max")),
                    level=item.get("level"),
                )
            )
        return sorted(periods, key=lambda period: period.start)

    def _expected_loads(self, now: datetime) -> list[ExpectedLoad]:
        """Antizipierte Großverbraucher mit bekanntem Startzeitpunkt.

        Aktuell ist das ausschliesslich die von der Warmwassersteuerung
        angekündigte Ladung. Die übrigen Verbraucher (Waschmaschine, Trockner,
        Spülmaschine) melden nur ihre Momentanleistung und keinen geplanten
        Start; sie werden deshalb nur als Diagnosewert geführt.
        """
        loads: list[ExpectedLoad] = []
        planned = self._state(self._option(CONF_DHW_PLANNED_START))
        start = _parse_datetime(planned)
        if start is not None and start > now:
            loads.append(
                ExpectedLoad(
                    name="Warmwasserbereitung",
                    start=start,
                    energy_kwh=float(self._option(CONF_DHW_ENERGY, DEFAULT_DHW_ENERGY)),
                )
            )
        return loads

    def current_load_power_w(self) -> float | None:
        return self._float_sum(CONF_LOAD_POWER_ENTITIES)

    def build_input(self) -> OptimizerInput:
        now = dt_util.now()
        return OptimizerInput(
            now=now,
            price_now=self._float(CONF_PRICE_NOW),
            price_avg_24h=self._float(CONF_PRICE_AVG_24H),
            price_min_today=self._float(CONF_PRICE_MIN_TODAY),
            price_max_today=self._float(CONF_PRICE_MAX_TODAY),
            cheap_periods=self._periods(CONF_CHEAP_PERIODS),
            expensive_periods=self._periods(CONF_EXPENSIVE_PERIODS),
            soc=self._float(CONF_BATTERY_SOC),
            battery_capacity_kwh=float(
                self._option(CONF_BATTERY_CAPACITY, DEFAULT_BATTERY_CAPACITY)
            ),
            round_trip_efficiency=float(
                self._option(CONF_ROUND_TRIP_EFFICIENCY, DEFAULT_ROUND_TRIP_EFFICIENCY)
            ),
            cycle_cost_ct_per_kwh=float(
                self._option(CONF_CYCLE_COST, DEFAULT_CYCLE_COST)
            ),
            min_soc=float(self._option(CONF_MIN_SOC, DEFAULT_MIN_SOC)),
            max_soc=float(self._option(CONF_MAX_SOC, DEFAULT_MAX_SOC)),
            max_charge_power_w=float(
                self._option(CONF_MAX_CHARGE_POWER, DEFAULT_MAX_CHARGE_POWER)
            ),
            pv_power_w=self._float(CONF_PV_POWER),
            grid_power_w=self._float_sum(CONF_GRID_POWER),
            house_power_w=self._float(CONF_HOUSE_POWER),
            pv_remaining_today_kwh=self._float_sum(CONF_PV_REMAINING_TODAY),
            pv_tomorrow_kwh=self._float_sum(CONF_PV_TOMORROW),
            surplus_threshold_w=float(
                self._option(CONF_SURPLUS_THRESHOLD, DEFAULT_SURPLUS_THRESHOLD)
            ),
            pv_reserve_enabled=bool(self._option(CONF_PV_RESERVE, True)),
            pv_reserve_threshold_kwh=float(
                self._option(CONF_PV_RESERVE_THRESHOLD, DEFAULT_PV_RESERVE_THRESHOLD)
            ),
            loads=self._expected_loads(now),
        )

    # --- Aktualisierung ----------------------------------------------------

    def _record(self, decision: Decision, now: datetime) -> None:
        """Hält eine Entscheidung fest, sobald sie sich inhaltlich ändert.

        Ohne diese Prüfung würde jeder Aktualisierungslauf einen Eintrag
        erzeugen und die Historie wäre nach fünf Minuten voller Duplikate.
        """
        if self.history:
            letzte = self.history[0]
            if (
                letzte.aktion == decision.action
                and letzte.begruendung == decision.reason
            ):
                return

        self.history.appendleft(
            DecisionRecord(
                zeit=now.isoformat(),
                aktion=decision.action,
                begruendung=decision.reason,
                erlaeuterung=decision.detail,
                ziel_soc=round(decision.target_soc, 1),
                ersparnis_ct=(
                    round(decision.savings_ct, 1)
                    if decision.savings_ct is not None
                    else None
                ),
                quelle=decision.source,
            )
        )

    async def _async_update_data(self) -> Decision:
        data = self.build_input()
        self.last_input = data
        decision = decide(data)

        if self._option(CONF_AI_ENABLED, False) and self._option(CONF_AI_TASK_ENTITY):
            decision = await self.advisor.refine(data, decision)

        self._record(decision, data.now)
        return decision


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parst ISO-Zeitstempel; naive Werte gelten als lokale Zeit.

    Die Warmwassersteuerung liefert `sensor.ww_v3_naechster_bestpreis_start`
    ohne Zeitzone ("2026-09-09 12:30:00"), die Tibber-Fenster dagegen mit
    Offset. Beide Formen müssen hier ankommen können.
    """
    if not isinstance(value, str) or not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return dt_util.as_local(parsed)
