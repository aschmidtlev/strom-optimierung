"""Optionaler KI-Pfad über die `ai_task`-Integration.

Die KI ist bewusst nur eine Verfeinerung: Grundlage bleibt immer die
regelbasierte Entscheidung aus `optimizer.decide()`. Fällt der KI-Aufruf aus –
kein API-Key, keine Antwort, unplausible Antwort – gilt unverändert die
Regelentscheidung. Die KI kann ausserdem nur zwischen denselben Aktionen
wählen und keinen Ziel-SoC ausserhalb der konfigurierten Grenzen setzen.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    ACTIONS,
    CONF_AI_TASK_ENTITY,
    SOURCE_AI,
    SOURCE_AI_FALLBACK,
)
from .optimizer import Decision, OptimizerInput

_LOGGER = logging.getLogger(__name__)

# Die KI wird nicht bei jedem Aktualisierungslauf befragt, sondern nur wenn
# sich die Regelentscheidung ändert oder dieser Abstand überschritten ist.
MIN_INTERVAL = timedelta(minutes=15)
TIMEOUT_SECONDS = 45

RESPONSE_STRUCTURE: dict[str, Any] = {
    "action": {
        "description": (
            "Eine der Aktionen: idle, charge_pv, charge_price, "
            "charge_anticipatory, hold"
        ),
        "required": True,
        "selector": {"text": None},
    },
    "target_soc": {
        "description": "Ziel-Ladestand in Prozent",
        "required": True,
        "selector": {"number": {"min": 0, "max": 100}},
    },
    "reason": {
        "description": "Kurze Begründung, höchstens acht Wörter",
        "required": True,
        "selector": {"text": None},
    },
    "detail": {
        "description": "Ausführliche Begründung in zwei bis drei Sätzen",
        "required": True,
        "selector": {"text": {"multiline": True}},
    },
}


class AiAdvisor:
    """Fragt optional ein Sprachmodell zur Ladeentscheidung."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._last_call: datetime | None = None
        self._last_rule_action: str | None = None

    def _entity_id(self) -> str | None:
        return self.entry.options.get(
            CONF_AI_TASK_ENTITY, self.entry.data.get(CONF_AI_TASK_ENTITY)
        )

    def _should_ask(self, rule_action: str) -> bool:
        now = dt_util.utcnow()
        if self._last_call is None:
            return True
        if rule_action != self._last_rule_action:
            return True
        return now - self._last_call >= MIN_INTERVAL

    async def refine(self, data: OptimizerInput, rule: Decision) -> Decision:
        """Verfeinert die Regelentscheidung, oder gibt sie unverändert zurück."""
        entity_id = self._entity_id()
        if not entity_id or self.hass.states.get(entity_id) is None:
            return rule
        if not self._should_ask(rule.action):
            return rule

        self._last_call = dt_util.utcnow()
        self._last_rule_action = rule.action

        try:
            response = await self.hass.services.async_call(
                "ai_task",
                "generate_data",
                {
                    "entity_id": entity_id,
                    "task_name": "Ladeentscheidung Batteriespeicher",
                    "instructions": _build_prompt(data, rule),
                    "structure": RESPONSE_STRUCTURE,
                },
                blocking=True,
                return_response=True,
            )
        except Exception:  # noqa: BLE001 - der KI-Pfad darf nie durchschlagen
            _LOGGER.warning(
                "KI-Abfrage fehlgeschlagen, Regelentscheidung bleibt gültig",
                exc_info=True,
            )
            return _as_fallback(rule)

        parsed = _extract(response)
        if parsed is None:
            _LOGGER.debug("KI-Antwort nicht auswertbar: %s", response)
            return _as_fallback(rule)

        return _merge(parsed, rule, data)


def _as_fallback(rule: Decision) -> Decision:
    rule.source = SOURCE_AI_FALLBACK
    return rule


def _extract(response: Any) -> dict[str, Any] | None:
    """Holt das Datenobjekt aus der Dienstantwort."""
    if isinstance(response, dict):
        data = response.get("data", response)
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                loaded = json.loads(data)
            except json.JSONDecodeError:
                return None
            return loaded if isinstance(loaded, dict) else None
    return None


def _merge(parsed: dict[str, Any], rule: Decision, data: OptimizerInput) -> Decision:
    """Übernimmt die KI-Antwort, aber nur innerhalb der erlaubten Grenzen."""
    action = str(parsed.get("action", "")).strip()
    if action not in ACTIONS:
        _LOGGER.debug("KI schlug unbekannte Aktion '%s' vor, verworfen", action)
        return _as_fallback(rule)

    try:
        target = float(parsed.get("target_soc", rule.target_soc))
    except (TypeError, ValueError):
        target = rule.target_soc
    target = max(data.min_soc, min(data.max_soc, target))

    reason = str(parsed.get("reason") or rule.reason)[:120]
    detail = str(parsed.get("detail") or rule.detail)

    if action != rule.action:
        detail = (
            f"{detail}\n\nRegelbasierte Alternative war '{rule.action}': "
            f"{rule.detail}"
        )

    rule.action = action
    rule.target_soc = target
    rule.reason = reason
    rule.detail = detail
    rule.source = SOURCE_AI
    return rule


def _build_prompt(data: OptimizerInput, rule: Decision) -> str:
    """Baut die Aufgabenbeschreibung für das Modell."""
    lines = [
        "Du entscheidest, ob ein Hausbatteriespeicher jetzt geladen werden soll.",
        "Ziel: Stromkosten senken, ohne unnötige Ladezyklen zu verbrauchen.",
        "",
        f"Zeitpunkt: {data.now:%d.%m.%Y %H:%M}",
        f"Speicherkapazität: {data.battery_capacity_kwh:.2f} kWh",
        f"Wirkungsgrad: {data.round_trip_efficiency:.0%}, "
        f"Zyklenkosten: {data.cycle_cost_ct_per_kwh:.1f} ct/kWh",
        f"Erlaubter SoC-Bereich: {data.min_soc:.0f} bis {data.max_soc:.0f} %",
        f"Aktueller SoC: {_fmt(data.soc, '%')}",
        f"Aktueller Preis: {_fmt(data.price_now, 'ct/kWh')}",
        f"Mittel 24 h: {_fmt(data.price_avg_24h, 'ct/kWh')}, "
        f"Tagesminimum: {_fmt(data.price_min_today, 'ct/kWh')}, "
        f"Tagesmaximum: {_fmt(data.price_max_today, 'ct/kWh')}",
        f"PV-Erzeugung jetzt: {_fmt(data.pv_power_w, 'W')}",
        f"Netzleistung: {_fmt(data.grid_power_w, 'W')} (negativ = Einspeisung)",
        f"PV-Prognose Rest heute: {_fmt(data.pv_remaining_today_kwh, 'kWh')}, "
        f"morgen: {_fmt(data.pv_tomorrow_kwh, 'kWh')} (Summe beider Anlagen)",
        "",
        "Günstige Preisfenster:",
        *_format_periods(data.cheap_periods, data.now),
        "",
        "Teure Preisfenster:",
        *_format_periods(data.expensive_periods, data.now),
        "",
        "Angekündigte Großverbraucher:",
        *(
            [
                f"- {load.name} ab {load.start:%d.%m. %H:%M}, "
                f"rund {load.energy_kwh:.1f} kWh"
                for load in data.loads
            ]
            or ["- keine"]
        ),
        "",
        f"Regelbasierte Empfehlung: {rule.action} mit Ziel-SoC "
        f"{rule.target_soc:.0f} % ({rule.reason}).",
        "",
        "Weiche nur davon ab, wenn du einen konkreten Vorteil benennen kannst.",
        "Laden aus dem Netz lohnt nur, wenn der später vermiedene Preis über "
        "dem durch den Wirkungsgrad erhöhten Ladepreis plus Zyklenkosten liegt.",
        "Antworte auf Deutsch.",
    ]
    if rule.missing:
        lines.extend(
            [
                "",
                "Diese Eingangswerte fehlen und dürfen nicht angenommen werden: "
                + ", ".join(rule.missing),
            ]
        )
    return "\n".join(lines)


def _fmt(value: float | None, unit: str) -> str:
    return "unbekannt" if value is None else f"{value:.1f} {unit}"


def _format_periods(periods: list, now: datetime) -> list[str]:
    upcoming = [p for p in periods if p.end > now]
    if not upcoming:
        return ["- keine"]
    return [
        f"- {p.start:%d.%m. %H:%M} bis {p.end:%H:%M}: "
        f"{p.price_mean:.1f} ct/kWh ({p.level or 'ohne Einstufung'})"
        for p in upcoming[:8]
    ]
