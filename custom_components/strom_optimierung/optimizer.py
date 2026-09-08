"""Regelbasierte Ladeentscheidung.

Dieses Modul ist bewusst frei von Home-Assistant-Importen: es arbeitet nur auf
einfachen Datenklassen. Dadurch ist die gesamte Entscheidungslogik ohne eine
laufende Home-Assistant-Instanz testbar (siehe `tests/test_optimizer.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .const import (
    ACTION_CHARGE_ANTICIPATORY,
    ACTION_CHARGE_PRICE,
    ACTION_CHARGE_PV,
    ACTION_HOLD,
    ACTION_IDLE,
    SOURCE_RULE,
)

HORIZON = timedelta(hours=24)


@dataclass(frozen=True)
class PricePeriod:
    """Ein zusammenhängendes Preisfenster aus dem Tibber-Attribut `periods`."""

    start: datetime
    end: datetime
    price_mean: float
    price_min: float | None = None
    price_max: float | None = None
    level: str | None = None

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment < self.end


@dataclass(frozen=True)
class ExpectedLoad:
    """Ein antizipierter Großverbraucher mit bekanntem Startzeitpunkt."""

    name: str
    start: datetime
    energy_kwh: float


@dataclass
class OptimizerInput:
    """Alle Eingangsgrößen einer Entscheidung."""

    now: datetime

    price_now: float | None = None
    price_avg_24h: float | None = None
    price_min_today: float | None = None
    price_max_today: float | None = None
    cheap_periods: list[PricePeriod] = field(default_factory=list)
    expensive_periods: list[PricePeriod] = field(default_factory=list)

    soc: float | None = None
    battery_capacity_kwh: float = 5.12
    round_trip_efficiency: float = 0.90
    cycle_cost_ct_per_kwh: float = 2.0
    min_soc: float = 10.0
    max_soc: float = 95.0
    max_charge_power_w: float = 2500.0

    pv_power_w: float | None = None
    grid_power_w: float | None = None
    house_power_w: float | None = None
    pv_remaining_today_kwh: float | None = None
    pv_tomorrow_kwh: float | None = None
    surplus_threshold_w: float = 300.0
    pv_reserve_enabled: bool = True
    pv_reserve_threshold_kwh: float = 10.0

    loads: list[ExpectedLoad] = field(default_factory=list)


@dataclass
class Decision:
    """Ergebnis einer Entscheidung."""

    action: str
    target_soc: float
    reason: str
    detail: str
    source: str = SOURCE_RULE
    charge_power_w: float | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    surplus_w: float | None = None
    expected_load_kwh: float = 0.0
    savings_ct: float | None = None
    missing: list[str] = field(default_factory=list)


# --- Hilfsfunktionen -------------------------------------------------------


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _kwh_to_soc(kwh: float, capacity_kwh: float) -> float:
    if capacity_kwh <= 0:
        return 0.0
    return kwh / capacity_kwh * 100.0


def calculate_surplus(data: OptimizerInput) -> float | None:
    """PV-Überschuss in Watt.

    Bevorzugt wird die Netzleistung: ein negativer Wert bedeutet Einspeisung,
    also Überschuss. Die Vorzeichenkonvention des Netzzählers ist nicht
    herstellerseitig verifiziert (siehe `docs/strom_v1_open_questions.md`, A1).
    Liegt keine Netzleistung vor, wird ersatzweise aus PV-Erzeugung minus
    Hausverbrauch gerechnet.
    """
    if data.grid_power_w is not None:
        return max(0.0, -data.grid_power_w)
    if data.pv_power_w is not None and data.house_power_w is not None:
        return max(0.0, data.pv_power_w - data.house_power_w)
    return None


def price_at(data: OptimizerInput, moment: datetime) -> float | None:
    """Erwarteter Preis zu einem Zeitpunkt, aus den bekannten Fenstern."""
    for period in (*data.expensive_periods, *data.cheap_periods):
        if period.contains(moment):
            return period.price_mean
    return data.price_avg_24h if data.price_avg_24h is not None else data.price_now


def upcoming_loads(data: OptimizerInput) -> list[ExpectedLoad]:
    """Antizipierte Großverbraucher innerhalb des Planungshorizonts."""
    horizon_end = data.now + HORIZON
    return sorted(
        (load for load in data.loads if data.now < load.start <= horizon_end),
        key=lambda load: load.start,
    )


def current_period(periods: list[PricePeriod], moment: datetime) -> PricePeriod | None:
    for period in periods:
        if period.contains(moment):
            return period
    return None


def cheapest_window_before(
    periods: list[PricePeriod], now: datetime, deadline: datetime
) -> PricePeriod | None:
    """Günstigstes noch nutzbares Fenster, das vor `deadline` beginnt."""
    candidates = [p for p in periods if p.start < deadline and p.end > now]
    if not candidates:
        return None
    return min(candidates, key=lambda p: p.price_mean)


def is_grid_charging_economic(
    price_charge: float, price_avoided: float, efficiency: float, cycle_cost: float
) -> bool:
    """Lohnt sich Netzladen, wenn damit späterer Bezug vermieden wird?

    Der Ladepreis wird um die Speicherverluste hochgerechnet und um einen
    Verschleissaufschlag ergänzt; erst wenn der vermiedene Preis darüber
    liegt, trägt sich der Zyklus.
    """
    if efficiency <= 0:
        return False
    return price_avoided > (price_charge / efficiency) + cycle_cost


# --- Ziel-SoC --------------------------------------------------------------


def _pv_expectation(data: OptimizerInput) -> tuple[float | None, str]:
    """Maßgebliche PV-Erwartung und deren Bezugszeitraum."""
    if (
        data.pv_remaining_today_kwh is not None
        and data.pv_remaining_today_kwh >= data.pv_reserve_threshold_kwh
    ):
        return data.pv_remaining_today_kwh, "heute"
    if data.pv_tomorrow_kwh is not None:
        return data.pv_tomorrow_kwh, "morgen"
    return data.pv_remaining_today_kwh, "heute"


def calculate_target_soc(data: OptimizerInput) -> tuple[float, str]:
    """Ziel-SoC aus antizipiertem Bedarf und PV-Prognose beider Anlagen.

    Grundsatz: günstig geladene Energie wird früher oder später ohnehin
    verbraucht, deshalb ist der Höchst-Ladestand der Ausgangswert. Begrenzt
    wird er allein durch die PV-Erwartung – und diese Begrenzung darf den
    Bedarf eines angekündigten Großverbrauchers nicht unterschreiten.
    """
    need_kwh = sum(load.energy_kwh for load in upcoming_loads(data))
    floor = _clamp(
        data.min_soc + _kwh_to_soc(need_kwh, data.battery_capacity_kwh),
        data.min_soc,
        data.max_soc,
    )
    target = data.max_soc
    notes = [f"Angekündigter Bedarf {need_kwh:.1f} kWh"]

    pv_expected, horizon = _pv_expectation(data)
    if (
        data.pv_reserve_enabled
        and pv_expected is not None
        and pv_expected >= data.pv_reserve_threshold_kwh
    ):
        # Ist reichlich PV zu erwarten, wird bewusst Ladekapazität freigehalten,
        # damit der Überschuss nicht in die Einspeisung läuft.
        reserve_pct = min(
            _kwh_to_soc(pv_expected, data.battery_capacity_kwh),
            data.max_soc - data.min_soc,
        )
        capped = max(floor, data.max_soc - reserve_pct)
        if capped < target:
            notes.append(
                f"PV-Reserve {horizon} {pv_expected:.1f} kWh begrenzt auf "
                f"{capped:.0f} %"
            )
            target = capped
        else:
            notes.append(f"PV-Prognose {horizon} {pv_expected:.1f} kWh")

    return _clamp(target, data.min_soc, data.max_soc), "; ".join(notes)


# --- Kernentscheidung ------------------------------------------------------


def decide(data: OptimizerInput) -> Decision:
    """Regelbasierte Ladeentscheidung."""
    missing = _missing_inputs(data)
    target_soc, target_note = calculate_target_soc(data)
    surplus = calculate_surplus(data)
    loads = upcoming_loads(data)
    load_kwh = sum(load.energy_kwh for load in loads)

    def build(
        action: str,
        reason: str,
        detail: str,
        *,
        target: float | None = None,
        power: float | None = None,
        window: PricePeriod | None = None,
        savings: float | None = None,
    ) -> Decision:
        return Decision(
            action=action,
            target_soc=target if target is not None else target_soc,
            reason=reason,
            detail=detail,
            charge_power_w=power,
            window_start=window.start if window else None,
            window_end=window.end if window else None,
            surplus_w=surplus,
            expected_load_kwh=load_kwh,
            savings_ct=savings,
            missing=missing,
        )

    # 1. Speicher voll: keine weitere Ladung, unabhängig von Preis und PV.
    if data.soc is not None and data.soc >= data.max_soc:
        return build(
            ACTION_HOLD,
            "Speicher voll",
            f"SoC {data.soc:.0f} % hat die Obergrenze {data.max_soc:.0f} % erreicht.",
        )

    # 2. PV-Überschuss hat Vorrang: dieser Strom kostet nichts und wäre sonst
    #    eingespeist.
    if surplus is not None and surplus >= data.surplus_threshold_w:
        return build(
            ACTION_CHARGE_PV,
            "PV-Überschuss",
            f"{surplus:.0f} W Überschuss über der Schwelle "
            f"{data.surplus_threshold_w:.0f} W – Ladung aus Eigenerzeugung.",
            target=data.max_soc,
            power=min(surplus, data.max_charge_power_w),
        )

    # Ohne Preisinformation ist keine wirtschaftliche Aussage möglich.
    if data.price_now is None:
        return build(
            ACTION_IDLE,
            "Keine Preisdaten",
            "Der aktuelle Strompreis ist nicht verfügbar; es wird nicht aus dem "
            "Netz geladen.",
        )

    soc_reached = data.soc is not None and data.soc >= target_soc

    # 3. Antizipatives Laden vor einem bekannten Großverbraucher.
    for load in loads:
        expected_price = price_at(data, load.start)
        if expected_price is None:
            continue
        window = cheapest_window_before(data.cheap_periods, data.now, load.start)
        charge_price = window.price_mean if window else data.price_now
        if not is_grid_charging_economic(
            charge_price,
            expected_price,
            data.round_trip_efficiency,
            data.cycle_cost_ct_per_kwh,
        ):
            continue

        savings = (
            expected_price - (charge_price / data.round_trip_efficiency)
            - data.cycle_cost_ct_per_kwh
        ) * load.energy_kwh

        if soc_reached:
            return build(
                ACTION_HOLD,
                "Bedarf gedeckt",
                f"Ziel-SoC {target_soc:.0f} % für '{load.name}' ist erreicht "
                f"({target_note}).",
                window=window,
                savings=savings,
            )

        in_window = window is not None and window.contains(data.now)
        if in_window or window is None:
            hours = max(
                (load.start - data.now).total_seconds() / 3600.0, 0.25
            )
            power = min(load.energy_kwh / hours * 1000.0, data.max_charge_power_w)
            where = (
                f"im günstigen Fenster ab {window.start:%H:%M} "
                f"({window.price_mean:.1f} ct/kWh)"
                if window
                else f"zum aktuellen Preis ({data.price_now:.1f} ct/kWh)"
            )
            return build(
                ACTION_CHARGE_ANTICIPATORY,
                f"Vorladen für {load.name}",
                f"'{load.name}' startet um {load.start:%d.%m. %H:%M} bei erwarteten "
                f"{expected_price:.1f} ct/kWh. Laden {where} spart rund "
                f"{savings:.0f} ct. Ziel-SoC {target_soc:.0f} % ({target_note}).",
                power=power,
                window=window,
                savings=savings,
            )

        return build(
            ACTION_HOLD,
            f"Warte auf Fenster für {load.name}",
            f"Günstigstes Fenster vor '{load.name}' beginnt um "
            f"{window.start:%d.%m. %H:%M} mit {window.price_mean:.1f} ct/kWh.",
            window=window,
            savings=savings,
        )

    # 4. Vorladen in einer allgemeinen Niedrigpreisphase.
    cheap_now = current_period(data.cheap_periods, data.now)
    if cheap_now is not None:
        avoided = _highest_expected_price(data)
        if avoided is not None and is_grid_charging_economic(
            cheap_now.price_mean,
            avoided,
            data.round_trip_efficiency,
            data.cycle_cost_ct_per_kwh,
        ):
            if soc_reached:
                return build(
                    ACTION_HOLD,
                    "Ziel-SoC erreicht",
                    f"Günstiges Fenster aktiv, aber SoC {data.soc:.0f} % deckt "
                    f"das Ziel von {target_soc:.0f} % ({target_note}).",
                    window=cheap_now,
                )
            usable = data.battery_capacity_kwh * (
                target_soc - (data.soc if data.soc is not None else data.min_soc)
            ) / 100.0
            savings = (
                avoided - (cheap_now.price_mean / data.round_trip_efficiency)
                - data.cycle_cost_ct_per_kwh
            ) * max(usable, 0.0)
            hours = max(
                (cheap_now.end - data.now).total_seconds() / 3600.0, 0.25
            )
            return build(
                ACTION_CHARGE_PRICE,
                "Günstiges Preisfenster",
                f"Aktuelles Fenster {cheap_now.price_mean:.1f} ct/kWh bis "
                f"{cheap_now.end:%H:%M}; später werden bis zu {avoided:.1f} ct/kWh "
                f"erwartet. Ziel-SoC {target_soc:.0f} % ({target_note}).",
                power=min(
                    max(usable, 0.0) / hours * 1000.0, data.max_charge_power_w
                ),
                window=cheap_now,
                savings=savings,
            )

    # 5. Kein Anlass zu laden.
    next_window = cheapest_window_before(
        data.cheap_periods, data.now, data.now + HORIZON
    )
    if next_window is not None and next_window.start > data.now:
        return build(
            ACTION_IDLE,
            "Warte auf günstiges Fenster",
            f"Nächstes günstiges Fenster ab {next_window.start:%d.%m. %H:%M} mit "
            f"{next_window.price_mean:.1f} ct/kWh. Aktuell "
            f"{data.price_now:.1f} ct/kWh.",
            window=next_window,
        )
    return build(
        ACTION_IDLE,
        "Kein Ladeanlass",
        f"Weder PV-Überschuss noch ein wirtschaftliches Preisfenster. Aktuell "
        f"{data.price_now:.1f} ct/kWh.",
    )


def _highest_expected_price(data: OptimizerInput) -> float | None:
    """Höchster erwarteter Preis im Horizont, gegen den sich Laden lohnt."""
    horizon_end = data.now + HORIZON
    future = [
        p.price_mean
        for p in data.expensive_periods
        if p.end > data.now and p.start <= horizon_end
    ]
    if future:
        return max(future)
    return data.price_max_today


def _missing_inputs(data: OptimizerInput) -> list[str]:
    """Fehlende Eingangsgrößen, die die Entscheidung einschränken."""
    missing: list[str] = []
    if data.soc is None:
        missing.append("Speicher-SoC")
    if data.price_now is None:
        missing.append("Aktueller Strompreis")
    if not data.cheap_periods:
        missing.append("Günstige Preisfenster")
    if data.grid_power_w is None and (
        data.pv_power_w is None or data.house_power_w is None
    ):
        missing.append("Netz-/PV-Leistung für Überschusserkennung")
    if data.pv_remaining_today_kwh is None and data.pv_tomorrow_kwh is None:
        missing.append("PV-Prognose")
    return missing
