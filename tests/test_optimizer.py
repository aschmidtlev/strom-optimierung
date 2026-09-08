"""Tests der regelbasierten Ladeentscheidung.

Die Zahlenwerte stammen aus dem Entity-Snapshot vom 08.09.2026
(`csv/harvest_2026-09-08-21-58-31.csv`), damit die Testfälle die reale
Preisstruktur der Zielanlage abbilden und nicht erfundene Werte.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.strom_optimierung.const import (
    ACTION_CHARGE_ANTICIPATORY,
    ACTION_CHARGE_PRICE,
    ACTION_CHARGE_PV,
    ACTION_HOLD,
    ACTION_IDLE,
)
from custom_components.strom_optimierung.optimizer import (
    ExpectedLoad,
    OptimizerInput,
    PricePeriod,
    calculate_surplus,
    calculate_target_soc,
    cheapest_window_before,
    decide,
    is_grid_charging_economic,
    price_at,
)

TZ = timezone(timedelta(hours=2))

# Günstiges Fenster laut Attribut `periods` von
# binary_sensor.home_bestpreis_zeitraum.
CHEAP = PricePeriod(
    start=datetime(2026, 9, 9, 12, 30, tzinfo=TZ),
    end=datetime(2026, 9, 9, 16, 30, tzinfo=TZ),
    price_mean=23.21,
    price_min=21.67,
    price_max=24.9,
    level="cheap",
)

# Teures Fenster laut Attribut `periods` von
# binary_sensor.home_spitzenpreis_zeitraum.
EXPENSIVE = PricePeriod(
    start=datetime(2026, 9, 9, 6, 15, tzinfo=TZ),
    end=datetime(2026, 9, 9, 9, 15, tzinfo=TZ),
    price_mean=38.05,
    price_min=35.65,
    price_max=41.15,
    level="expensive",
)


def base_input(**overrides) -> OptimizerInput:
    data = OptimizerInput(
        now=datetime(2026, 9, 9, 13, 0, tzinfo=TZ),
        price_now=23.21,
        price_avg_24h=32.1,
        price_min_today=14.96,
        price_max_today=47.29,
        cheap_periods=[CHEAP],
        expensive_periods=[EXPENSIVE],
        soc=40.0,
        battery_capacity_kwh=5.12,
        pv_remaining_today_kwh=0.0,
        pv_tomorrow_kwh=0.0,
        grid_power_w=670.0,
    )
    for key, value in overrides.items():
        setattr(data, key, value)
    return data


# --- Hilfsfunktionen -------------------------------------------------------


def test_surplus_from_negative_grid_power():
    """Einspeisung wird als Überschuss gewertet."""
    assert calculate_surplus(base_input(grid_power_w=-1500.0)) == 1500.0


def test_surplus_zero_while_importing():
    assert calculate_surplus(base_input(grid_power_w=670.0)) == 0.0


def test_surplus_falls_back_to_pv_minus_house():
    data = base_input(grid_power_w=None, pv_power_w=4200.0, house_power_w=671.0)
    assert calculate_surplus(data) == pytest.approx(3529.0)


def test_surplus_unknown_without_any_source():
    data = base_input(grid_power_w=None, pv_power_w=None, house_power_w=None)
    assert calculate_surplus(data) is None


def test_price_at_uses_matching_window():
    data = base_input()
    assert price_at(data, datetime(2026, 9, 9, 7, 0, tzinfo=TZ)) == 38.05
    assert price_at(data, datetime(2026, 9, 9, 13, 0, tzinfo=TZ)) == 23.21


def test_price_at_falls_back_to_average():
    data = base_input()
    assert price_at(data, datetime(2026, 9, 9, 20, 0, tzinfo=TZ)) == 32.1


def test_cheapest_window_before_deadline():
    data = base_input(now=datetime(2026, 9, 9, 5, 0, tzinfo=TZ))
    window = cheapest_window_before(
        data.cheap_periods, data.now, datetime(2026, 9, 9, 18, 0, tzinfo=TZ)
    )
    assert window is CHEAP


def test_cheapest_window_ignores_windows_after_deadline():
    data = base_input(now=datetime(2026, 9, 9, 5, 0, tzinfo=TZ))
    window = cheapest_window_before(
        data.cheap_periods, data.now, datetime(2026, 9, 9, 8, 0, tzinfo=TZ)
    )
    assert window is None


def test_round_trip_economics():
    # 23.21 / 0.9 + 2.0 = 27.79; 38.05 liegt darüber, 28.00 nicht.
    assert is_grid_charging_economic(23.21, 38.05, 0.9, 2.0) is True
    assert is_grid_charging_economic(23.21, 28.00, 0.9, 2.0) is False


# --- Ziel-SoC --------------------------------------------------------------


DHW_LOAD = ExpectedLoad(
    name="Warmwasserbereitung",
    start=datetime(2026, 9, 9, 18, 0, tzinfo=TZ),
    energy_kwh=3.1,
)


def test_target_soc_defaults_to_maximum_without_pv_expectation():
    """Ohne PV-Erwartung ist der Höchst-Ladestand das Ziel."""
    target, note = calculate_target_soc(base_input(loads=[DHW_LOAD]))
    assert target == 95.0
    assert "3.1 kWh" in note


def test_target_soc_capped_by_pv_forecast():
    """Bei viel PV wird Ladekapazität für den Überschuss freigehalten."""
    data = base_input(
        pv_remaining_today_kwh=0.0,
        pv_tomorrow_kwh=28.3,  # Summe beider Anlagen: 17.952 + 10.389
        pv_reserve_threshold_kwh=10.0,
    )
    target, note = calculate_target_soc(data)
    assert target == 10.0
    assert "PV-Reserve" in note


def test_pv_reserve_never_undercuts_announced_load():
    """Ein angekündigter Verbraucher hat Vorrang vor der PV-Reserve."""
    data = base_input(
        loads=[DHW_LOAD],
        pv_remaining_today_kwh=0.0,
        pv_tomorrow_kwh=28.3,
        pv_reserve_threshold_kwh=10.0,
    )
    target, _ = calculate_target_soc(data)
    # 3.1 kWh von 5.12 kWh entsprechen 60.5 Prozentpunkten über min_soc.
    assert target == pytest.approx(70.5, abs=0.2)


def test_target_soc_ignores_pv_reserve_when_disabled():
    data = base_input(pv_tomorrow_kwh=28.3, pv_reserve_enabled=False)
    target, _ = calculate_target_soc(data)
    assert target == 95.0


def test_target_soc_never_exceeds_max():
    load = ExpectedLoad(
        name="Warmwasserbereitung",
        start=datetime(2026, 9, 9, 18, 0, tzinfo=TZ),
        energy_kwh=99.0,
    )
    data = base_input(loads=[load], max_soc=95.0)
    target, _ = calculate_target_soc(data)
    assert target == 95.0


# --- Entscheidungen --------------------------------------------------------


def test_pv_surplus_wins_over_price():
    data = base_input(grid_power_w=-1500.0)
    decision = decide(data)
    assert decision.action == ACTION_CHARGE_PV
    assert decision.target_soc == data.max_soc
    assert decision.charge_power_w == 1500.0


def test_pv_surplus_below_threshold_is_ignored():
    data = base_input(grid_power_w=-100.0, surplus_threshold_w=300.0)
    assert decide(data).action != ACTION_CHARGE_PV


def test_full_battery_holds_even_with_surplus():
    data = base_input(soc=95.0, grid_power_w=-1500.0)
    decision = decide(data)
    assert decision.action == ACTION_HOLD
    assert "voll" in decision.reason.lower()


def test_cheap_window_triggers_price_charging():
    data = base_input(soc=20.0)
    decision = decide(data)
    assert decision.action == ACTION_CHARGE_PRICE
    assert decision.window_start == CHEAP.start
    assert decision.savings_ct is not None and decision.savings_ct > 0


def test_cheap_window_holds_when_pv_reserve_lowers_target():
    """Sonniger Folgetag: trotz günstigem Fenster wird nicht nachgeladen."""
    data = base_input(soc=90.0, pv_tomorrow_kwh=28.3, pv_reserve_threshold_kwh=10.0)
    decision = decide(data)
    assert decision.action == ACTION_HOLD
    assert decision.target_soc == 10.0


def test_no_charging_without_price_data():
    data = base_input(price_now=None)
    decision = decide(data)
    assert decision.action == ACTION_IDLE
    assert "Aktueller Strompreis" in decision.missing


def test_anticipatory_charging_before_announced_load():
    """Warmwasserladung im teuren Fenster, günstiges Fenster liegt davor."""
    load = ExpectedLoad(
        name="Warmwasserbereitung",
        start=datetime(2026, 9, 9, 7, 0, tzinfo=TZ),
        energy_kwh=3.1,
    )
    cheap_before = PricePeriod(
        start=datetime(2026, 9, 9, 2, 0, tzinfo=TZ),
        end=datetime(2026, 9, 9, 5, 0, tzinfo=TZ),
        price_mean=21.67,
        level="very_cheap",
    )
    data = base_input(
        now=datetime(2026, 9, 9, 3, 0, tzinfo=TZ),
        price_now=21.67,
        cheap_periods=[cheap_before],
        loads=[load],
        soc=20.0,
    )
    decision = decide(data)
    assert decision.action == ACTION_CHARGE_ANTICIPATORY
    assert "Warmwasserbereitung" in decision.reason
    assert decision.charge_power_w is not None
    assert decision.charge_power_w <= data.max_charge_power_w


def test_anticipatory_waits_for_cheaper_window():
    """Vor dem günstigen Fenster wird nicht zum teureren Preis geladen."""
    load = ExpectedLoad(
        name="Warmwasserbereitung",
        start=datetime(2026, 9, 9, 7, 0, tzinfo=TZ),
        energy_kwh=3.1,
    )
    cheap_later = PricePeriod(
        start=datetime(2026, 9, 9, 4, 0, tzinfo=TZ),
        end=datetime(2026, 9, 9, 6, 0, tzinfo=TZ),
        price_mean=21.67,
        level="very_cheap",
    )
    data = base_input(
        now=datetime(2026, 9, 9, 2, 0, tzinfo=TZ),
        price_now=30.0,
        cheap_periods=[cheap_later],
        loads=[load],
        soc=20.0,
    )
    decision = decide(data)
    assert decision.action == ACTION_HOLD
    assert decision.window_start == cheap_later.start


def test_anticipatory_skipped_when_uneconomic():
    """Liegt der erwartete Preis kaum über dem Ladepreis, wird nicht geladen."""
    load = ExpectedLoad(
        name="Warmwasserbereitung",
        start=datetime(2026, 9, 9, 14, 0, tzinfo=TZ),
        energy_kwh=3.1,
    )
    data = base_input(
        now=datetime(2026, 9, 9, 13, 0, tzinfo=TZ),
        price_now=23.21,
        expensive_periods=[],
        price_max_today=24.0,
        loads=[load],
        soc=20.0,
    )
    decision = decide(data)
    assert decision.action not in (ACTION_CHARGE_ANTICIPATORY, ACTION_CHARGE_PRICE)


def test_missing_soc_is_reported_but_does_not_block():
    data = base_input(soc=None)
    decision = decide(data)
    assert "Speicher-SoC" in decision.missing
    assert decision.action in (ACTION_CHARGE_PRICE, ACTION_IDLE, ACTION_HOLD)


def test_idle_announces_next_window():
    data = base_input(
        now=datetime(2026, 9, 9, 10, 0, tzinfo=TZ),
        price_now=34.16,
        soc=50.0,
    )
    decision = decide(data)
    assert decision.action == ACTION_IDLE
    assert decision.window_start == CHEAP.start


def test_loads_beyond_horizon_are_ignored():
    load = ExpectedLoad(
        name="Warmwasserbereitung",
        start=datetime(2026, 9, 11, 7, 0, tzinfo=TZ),
        energy_kwh=3.1,
    )
    data = base_input(loads=[load])
    assert decide(data).expected_load_kwh == 0.0
