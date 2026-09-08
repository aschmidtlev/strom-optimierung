"""Konstanten und Konfigurationsschlüssel der Integration strom_optimierung."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "strom_optimierung"

# --- Konfigurationsschlüssel: Quell-Entities -------------------------------

CONF_PRICE_NOW: Final = "price_now_entity"
CONF_PRICE_AVG_24H: Final = "price_avg_24h_entity"
CONF_PRICE_MIN_TODAY: Final = "price_min_today_entity"
CONF_PRICE_MAX_TODAY: Final = "price_max_today_entity"
CONF_CHEAP_PERIODS: Final = "cheap_periods_entity"
CONF_EXPENSIVE_PERIODS: Final = "expensive_periods_entity"

# Je Zeithorizont eine Liste von Prognose-Entities. Die Liste nimmt die
# Sensoren *beider* PV-Anlagen auf und wird summiert; welche der beiden
# Forecast.Solar-Instanzen Ost bzw. West ist, muss dafür nicht bekannt sein.
CONF_PV_REMAINING_TODAY: Final = "pv_remaining_today_entities"
CONF_PV_TOMORROW: Final = "pv_tomorrow_entities"
CONF_PV_POWER: Final = "pv_power_entity"
CONF_GRID_POWER: Final = "grid_power_entities"
CONF_HOUSE_POWER: Final = "house_power_entity"

# Der SoC ist optional: der Marstek Venus war zum Zeitpunkt der Entwicklung
# hardwareseitig ausgefallen. Ohne SoC arbeitet die Logik eingeschränkt weiter
# und meldet das über binary_sensor.*_datenbasis_unvollstaendig.
CONF_BATTERY_SOC: Final = "battery_soc_entity"

CONF_DHW_PLANNED_START: Final = "dhw_planned_start_entity"
CONF_LOAD_POWER_ENTITIES: Final = "load_power_entities"

CONF_AI_TASK_ENTITY: Final = "ai_task_entity"

# --- Konfigurationsschlüssel: Parameter ------------------------------------

CONF_BATTERY_CAPACITY: Final = "battery_capacity_kwh"
CONF_ROUND_TRIP_EFFICIENCY: Final = "round_trip_efficiency"
CONF_CYCLE_COST: Final = "cycle_cost_ct_per_kwh"
CONF_MIN_SOC: Final = "min_soc"
CONF_MAX_SOC: Final = "max_soc"
CONF_MAX_CHARGE_POWER: Final = "max_charge_power_w"
CONF_SURPLUS_THRESHOLD: Final = "surplus_threshold_w"
CONF_DHW_ENERGY: Final = "dhw_energy_kwh"
CONF_PV_RESERVE: Final = "pv_reserve_enabled"
CONF_PV_RESERVE_THRESHOLD: Final = "pv_reserve_threshold_kwh"
CONF_AI_ENABLED: Final = "ai_enabled"

# --- Vorgabewerte ----------------------------------------------------------

# Marstek Venus E: 5,12 kWh nutzbar laut Herstellerangabe. Wird im
# Config-Flow abgefragt, da der Anwender ein anderes Modell haben kann.
DEFAULT_BATTERY_CAPACITY: Final = 5.12

# sensor.marstek_venus_modbus_gesamt_roundtrip_effizienz war im Snapshot
# "unknown"; dieser Wert dient als Vorgabe, bis der Sensor liefert.
DEFAULT_ROUND_TRIP_EFFICIENCY: Final = 0.90

# Verschleissaufschlag je durchgesetzter kWh. Konservative Vorgabe; verhindert,
# dass die Logik für Bruchteile eines Cents einen Ladezyklus verbraucht.
DEFAULT_CYCLE_COST: Final = 2.0

DEFAULT_MIN_SOC: Final = 10.0
DEFAULT_MAX_SOC: Final = 95.0
DEFAULT_MAX_CHARGE_POWER: Final = 2500.0
DEFAULT_SURPLUS_THRESHOLD: Final = 300.0

# Mittelwert je Warmwasser-Ladung, abgeleitet aus den EMS-ESP-Zählerständen
# des Nachbarprojekts ww_v3: sensor.boiler_dhw_nrgconscomp (8319 kWh) geteilt
# durch sensor.boiler_dhw_startshp (2649 Starts) ergibt rund 3,14 kWh.
DEFAULT_DHW_ENERGY: Final = 3.1

DEFAULT_PV_RESERVE_THRESHOLD: Final = 10.0

UPDATE_INTERVAL_SECONDS: Final = 60

# --- Entscheidungen --------------------------------------------------------

ACTION_IDLE: Final = "idle"
ACTION_CHARGE_PV: Final = "charge_pv"
ACTION_CHARGE_PRICE: Final = "charge_price"
ACTION_CHARGE_ANTICIPATORY: Final = "charge_anticipatory"
ACTION_HOLD: Final = "hold"

ACTIONS: Final = [
    ACTION_IDLE,
    ACTION_CHARGE_PV,
    ACTION_CHARGE_PRICE,
    ACTION_CHARGE_ANTICIPATORY,
    ACTION_HOLD,
]

SOURCE_RULE: Final = "rule"
SOURCE_AI: Final = "ai"
SOURCE_AI_FALLBACK: Final = "ai_fallback"
