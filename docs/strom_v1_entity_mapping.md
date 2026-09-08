# strom_v1 – Entity-Mapping

Jede von der Integration referenzierte externe Entity mit Beleg aus dem
Entity-Snapshot im Ordner `csv/` (Developer-Tools-Export vom 08.09.2026,
23:49–00:15 Uhr). Zustandswerte sind die des Snapshots.

> **Die Snapshots selbst sind nicht Teil dieses Repositories.** Sie enthalten
> Netzwerk- und Verbrauchsdaten (WLAN-SSID, interne IP-Adressen, Kosten- und
> Zählerstände) und stehen deshalb in `.gitignore`. Die hier zitierten
> Quellzeilen und Zustandswerte dokumentieren den geprüften Stand; die
> Dateien liegen auf dem Entwicklungsrechner.

Legende: **Pflicht** = ohne diese Entity ist keine Entscheidung möglich;
**optional** = verbessert die Entscheidung, ihr Fehlen wird über
`binary_sensor.*_datenbasis_unvollstaendig` gemeldet.

## Strompreis (Tibber)

| Entity | Snapshot-Wert | Rolle | Quellzeile |
|---|---|---|---|
| `sensor.home_aktueller_strompreis` | 34.16 ct/kWh | Pflicht – aktueller Preis | `harvest_2026-09-08-21-58-31.csv:29` |
| `binary_sensor.home_bestpreis_zeitraum` | off, Attribut `periods` mit 2 Fenstern | Pflicht – günstige Ladefenster | `harvest_2026-09-08-21-58-31.csv:2` |
| `binary_sensor.home_spitzenpreis_zeitraum` | off, Attribut `periods` mit 4 Fenstern | Pflicht – zu vermeidende Hochpreisfenster | `harvest_2026-09-08-21-58-31.csv:8` |
| `sensor.home_preis_vorlaufend_24h` | 32.1 ct/kWh | optional – Rückfallwert für Zeitpunkte ohne Fenster | `harvest_2026-09-08-21-58-31.csv:61` |
| `sensor.home_mindestpreis_heute` | 14.96 ct/kWh | optional – Anzeige | `harvest_2026-09-08-21-58-31.csv:44` |
| `sensor.home_hochstpreis_heute` | 47.29 ct/kWh | optional – Rückfallwert für den vermiedenen Preis | `harvest_2026-09-08-21-58-31.csv:42` |

Das Attribut `periods` beider Zeitraum-Sensoren ist die tragende Datenquelle.
Es enthält je Fenster `start`, `end`, `price_mean`, `price_min`, `price_max`
und `level`, für heute **und** morgen. Beispiel aus dem Snapshot: günstiges
Fenster 09.09. 12:30–16:30 mit 23.21 ct/kWh Mittel; teures Fenster
09.09. 06:15–09:15 mit 38.05 ct/kWh Mittel.

## PV-Prognose (zwei Forecast.Solar-Instanzen)

| Entity | Snapshot-Wert | Rolle | Quellzeile |
|---|---|---|---|
| `sensor.energy_production_today_remaining` | 0.0 kWh | optional – Restprognose Anlage 1 | `harvest_2026-09-08-21-59-56.csv:8` |
| `sensor.energy_production_today_remaining_2` | 0.0 kWh | optional – Restprognose Anlage 2 | `harvest_2026-09-08-21-59-56.csv:9` |
| `sensor.energy_production_tomorrow` | 17.952 kWh | optional – Prognose morgen Anlage 1 | `harvest_2026-09-08-21-59-56.csv:10` |
| `sensor.energy_production_tomorrow_2` | 10.389 kWh | optional – Prognose morgen Anlage 2 | `harvest_2026-09-08-21-59-56.csv:11` |

Beide Anlagen gehen je Zeithorizont als **Summe** in die Rechnung ein. Welche
Instanz Ost und welche West ist, muss dafür nicht bekannt sein – siehe
`strom_v1_open_questions.md`, A2.

## PV-Ist-Erzeugung und Netz

| Entity | Snapshot-Wert | Rolle | Quellzeile |
|---|---|---|---|
| `sensor.stp10_0_3av_40_040_pv_power` | 0 W | optional – Erzeugung jetzt | `harvest_2026-09-08-22-01-12.csv:30` |
| `sensor.shellypro3em_ecc9ffe7c9dc_phase_a_leistung` | 270.3 W | Netzleistung Phase A | `harvest_2026-09-08-22-15-24.csv:4` |
| `sensor.shellypro3em_ecc9ffe7c9dc_phase_b_leistung` | 53.9 W | Netzleistung Phase B | `harvest_2026-09-08-22-15-24.csv:7` |
| `sensor.shellypro3em_ecc9ffe7c9dc_phase_c_leistung` | 341.1 W | Netzleistung Phase C | `harvest_2026-09-08-22-15-24.csv:10` |
| `sensor.ww_v3_hausverbrauch_berechnet` | 671 W | optional – Ersatzpfad für Überschuss | `harvest_2026-09-08-21-58-43.csv:45` |

**Beleg, dass der Shelly Pro 3EM der Netzzähler ist:** die Phasensumme des
Snapshots vom 29.08.2026 (227.0 + 49.9 + 423.0 = 699.9 W) stimmt exakt mit
`sensor.evu_leistung` (699.871 W) und `sensor.netzbezug_aktuell` (699.871 W)
desselben Zeitpunkts überein
(`../WW-Steuerung/Copilot/harvest_2026-08-29-22-35-33.csv`). Im aktuellen
Snapshot ergibt die Summe 665.3 W gegenüber `sensor.tibber_pulse_home_energie`
mit 670 W bei PV = 0.

## Batteriespeicher

| Entity | Snapshot-Wert | Rolle | Quellzeile |
|---|---|---|---|
| `sensor.marstek_venus_modbus_soc_batterie` | **unavailable** | optional – Ladestand | `harvest_2026-09-08-21-58-43.csv:37` |

Alle 22 Marstek-Entities des Snapshots sind `unavailable` oder `unknown`,
`binary_sensor.marstek_venus_modbus_modbus_verbindung` steht auf `off`
(`harvest_2026-09-08-21-58-43.csv:2`). Der SoC wird deshalb **nicht** als
Vorschlagswert im Konfigurationsdialog gesetzt und ist als optional
behandelt. **Keine Steuer-Entity wird referenziert** – siehe
`strom_v1_open_questions.md`, A3.

## Großverbraucher

| Entity | Snapshot-Wert | Rolle | Quellzeile |
|---|---|---|---|
| `sensor.ww_v3_naechster_bestpreis_start` | 2026-09-09 12:30:00 | optional – angekündigte Warmwasserladung | `harvest_2026-09-08-22-02-18.csv:15` |
| `sensor.waschmaschine_energy_power` | 0 W | nur Diagnose | `harvest_2026-09-08-22-09-51.csv:6` |
| `sensor.trockner_aktuelle_leistung` | 0.0 W | nur Diagnose | `harvest_2026-09-08-22-09-59.csv:11` |
| `sensor.spuehlmaschine_energy_power` | 0 W | nur Diagnose | `harvest_2026-09-08-22-10-06.csv:7` |

Nur die Warmwasserbereitung kündigt ihren Start an und kann deshalb
antizipativ eingeplant werden. Waschmaschine, Trockner und Spülmaschine
liefern ausschliesslich Momentanleistung; sie werden als Diagnosewert
geführt und **nicht** automatisiert.

## KI-Pfad

| Entity | Snapshot-Wert | Rolle | Quellzeile |
|---|---|---|---|
| `ai_task.claude_ai_task` | unknown (Entity vorhanden) | optional – Verfeinerung der Entscheidung | `harvest_2026-09-08-21-58-56.csv:2` |

## Zusätzliche Referenzen des Dashboards

`strom_v1_dashboard.yaml` zeigt über die oben gelisteten hinaus weitere
Entities rein zur Anzeige – Preisniveau, Preismuster, Volatilität,
Wechselrichterzustand, Tibber-Zähler, Warmwasserstatus. Insgesamt referenziert
das Dashboard 83 Entities: 13 davon erzeugt die Integration selbst, die
übrigen 70 sind in den Snapshots belegt, keine ist unauflösbar. Die
Einzelprüfung ist in `strom_v1_quality_report.md`, Abschnitt 1.2b,
festgehalten.

Zwei dieser Referenzen stehen im Snapshot auf `unavailable`
(`sensor.marstek_venus_modbus_soc_batterie`,
`sensor.marstek_venus_modbus_batterieleistung`). Sie erscheinen nur in
auskommentierten Zeilen sowie – beim Ladestand – in einem Zweig, der
ausschliesslich bei bestehender Modbus-Verbindung gerendert wird.

## Bewusst nicht referenziert

| Entity | Grund |
|---|---|
| `select.marstek_venus_modbus_benutzer_modus` | Einziger denkbarer Steuerkandidat, Zustand `unknown`, Optionsliste unbekannt. Wird nicht geraten. |
| `switch.marstek_venus_modbus_backup_funktion` | Zustand `unknown`, Wirkung nicht aus den Daten ableitbar. |
| `sensor.marstek_venus_modbus_batterieleistung` | `unavailable`; Vorzeichenkonvention laut `../WW-Steuerung/ww_v3_open_questions.md` B6 unverifiziert. |
| `sensor.gesamtleistung_haushalt` | Laut `../WW-Steuerung/ww_v3_open_questions.md` B6 misst die Entity vermutlich nur einen Teil-Stromkreis. |
| alle `*.tibber_preis_*`, `ww_tibber_*`, `ww_v1_8_*`, `ww_v2_*` | Im Snapshot durchgängig `unavailable`. |
