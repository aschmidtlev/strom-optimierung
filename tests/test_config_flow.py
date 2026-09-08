"""Tests des Konfigurationsdialogs.

Der Schwerpunkt liegt auf dem Bau der Schemata. Ein Selector, dessen
Konfiguration das Schema von Home Assistant verletzt, wirft erst beim
Anzeigen des Formulars – und erscheint dem Anwender dann nur als
"Unknown error occurred", ohne Hinweis auf die Ursache. Genau das ist
einmal passiert: `unit_of_measurement=None` am einheitenlosen Feld
Wirkungsgrad, siehe docs/strom_v1_changelog.md.
"""

from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.strom_optimierung.config_flow import (
    SUGGESTED,
    _number,
    _strip_empty,
    battery_schema,
    loads_schema,
    price_schema,
    pv_schema,
)
from custom_components.strom_optimierung.const import (
    CONF_MAX_SOC,
    CONF_MIN_SOC,
    CONF_PRICE_NOW,
)

ALL_SCHEMAS = (price_schema, pv_schema, battery_schema, loads_schema)


@pytest.mark.parametrize("builder", ALL_SCHEMAS)
def test_schema_builds_with_suggestions(builder):
    """Jedes Schema muss sich mit den Vorschlagswerten bauen lassen."""
    assert isinstance(builder(SUGGESTED), vol.Schema)


@pytest.mark.parametrize("builder", ALL_SCHEMAS)
def test_schema_builds_without_defaults(builder):
    """Und ebenso ohne jede Vorbelegung."""
    assert isinstance(builder({}), vol.Schema)


def test_number_selector_without_unit():
    """Ein einheitenloses Zahlenfeld darf kein leeres unit_of_measurement setzen.

    Der Wirkungsgrad ist das einzige Feld ohne Einheit. Wird der Schlüssel mit
    `None` gesetzt statt weggelassen, weist das Selector-Schema ihn zurück und
    der gesamte Dialogschritt bricht ab.
    """
    ohne_einheit = _number(0.5, 1.0, 0.01)
    assert "unit_of_measurement" not in ohne_einheit.config

    mit_einheit = _number(0, 100, 1, "%")
    assert mit_einheit.config["unit_of_measurement"] == "%"


def test_battery_schema_accepts_plausible_input():
    """Ein realistischer Satz Werte muss die Validierung bestehen."""
    schema = battery_schema(SUGGESTED)
    validiert = schema(
        {
            "battery_capacity_kwh": 5.12,
            "round_trip_efficiency": 0.9,
            "cycle_cost_ct_per_kwh": 2.0,
            "min_soc": 10,
            "max_soc": 95,
            "max_charge_power_w": 2500,
            "surplus_threshold_w": 300,
            "pv_reserve_enabled": True,
            "pv_reserve_threshold_kwh": 10,
        }
    )
    assert validiert["round_trip_efficiency"] == 0.9


def test_price_schema_requires_mandatory_fields():
    """Die Pflichtfelder der Preisquellen dürfen nicht entfallen."""
    with pytest.raises(vol.Invalid):
        price_schema(SUGGESTED)({})


def test_suggested_entities_are_plausible_ids():
    """Die Vorschlagswerte müssen gültige Entity-IDs sein."""
    for wert in SUGGESTED.values():
        for entity_id in wert if isinstance(wert, list) else [wert]:
            domain, _, objekt = entity_id.partition(".")
            assert domain and objekt, f"keine gültige Entity-ID: {entity_id}"


def test_suggested_soc_is_absent():
    """Der Speicher-Ladestand wird bewusst nicht vorgeschlagen.

    Er war im Snapshot `unavailable`; eine Vorbelegung würde eine Quelle
    vortäuschen, die keine Daten liefert.
    """
    assert "battery_soc_entity" not in SUGGESTED


def test_strip_empty_removes_blank_selections():
    bereinigt = _strip_empty(
        {
            CONF_PRICE_NOW: "sensor.home_aktueller_strompreis",
            "leer_text": "",
            "leer_none": None,
            "leer_liste": [],
            CONF_MIN_SOC: 0,
            CONF_MAX_SOC: 95,
        }
    )
    assert bereinigt == {
        CONF_PRICE_NOW: "sensor.home_aktueller_strompreis",
        CONF_MIN_SOC: 0,
        CONF_MAX_SOC: 95,
    }


def test_strip_empty_keeps_zero():
    """Die Null ist ein gültiger Grenzwert und darf nicht wegfallen."""
    assert _strip_empty({CONF_MIN_SOC: 0}) == {CONF_MIN_SOC: 0}
