# strom_v1 – Offene Fragen: Status

## Teil A – Vor der Implementierung geklärt (Session vom 09.09.2026)

| # | Frage | Antwort des Anwenders | Umsetzung |
|---|---|---|---|
| A1 | Deliverable-Format: HACS-Python-Integration oder YAML-Package wie `ww_v3`? | Python-`custom_component` für HACS | `custom_components/strom_optimierung/` mit `config_flow`, `DataUpdateCoordinator`, Plattformen `sensor`/`binary_sensor` |
| A2 | Marstek-Steuerung: alle Entities `unavailable`, Optionsliste des Benutzer-Modus unbekannt | Zunächst nur Entscheidungslogik ohne Aktor | Die Integration setzt **keinen** Schaltbefehl ab. Sie liefert Empfehlung, Ziel-SoC, Ladefenster und Begründung. |
| A3 | Netzdaten fehlten im `csv`-Ordner | Nachgeliefert: `harvest_2026-09-08-22-15-24.csv` mit Shelly Pro 3EM | Netzleistung als Summe der drei Phasen; Beleg siehe `strom_v1_entity_mapping.md` |

## Teil B – Getroffene Annahmen (nicht blockierend, aber zu kennen)

**B1. Vorzeichenkonvention des Shelly Pro 3EM ist nicht verifiziert.**
Die Integration nimmt an: **positiv = Netzbezug, negativ = Einspeisung**. Das
entspricht der üblichen Shelly-Konvention, konnte aber aus den vorliegenden
Snapshots nicht belegt werden – beide Aufnahmen entstanden nachts bei PV = 0,
alle Phasenwerte waren positiv.
*Auswirkung, falls die Annahme falsch ist:* `sensor.*_pv_ueberschuss` bliebe
dauerhaft 0 und die PV-Überschussladung würde nie empfohlen. Eine
Fehlsteuerung ist ausgeschlossen, da kein Aktor angesteuert wird.
→ *Zur Klärung nötig:* eine Ablesung der drei Phasenwerte zu einem Zeitpunkt
mit belegter Einspeisung (PV-Leistung deutlich über Hausverbrauch). Ergibt die
Summe dann einen negativen Wert, ist die Annahme bestätigt.

**B2. Ost/West-Zuordnung der beiden PV-Anlagen ist nicht bestimmt – und wird
auch nicht benötigt.**
Aus den Spitzenzeiten (`sensor.power_highest_peak_time_today` 10:00 UTC gegen
`_2` 15:00 UTC) liesse sich eine Ost-/West-Zuordnung *vermuten*. Die
Integration verzichtet bewusst darauf: sie summiert je Zeithorizont die
Sensoren beider Anlagen. Damit entfällt die Annahme vollständig.
→ *Keine Aktion nötig.* Sollte später eine richtungsabhängige Logik gewünscht
sein (etwa: Ost-Ertrag früher einplanen), müsste die Zuordnung zuvor am Gerät
bestätigt werden.

**B3. Energiebedarf je Warmwasser-Ladung ist ein abgeleiteter Vorgabewert.**
Der Vorgabewert 3.1 kWh stammt aus den EMS-ESP-Zählerständen des
Nachbarprojekts: `sensor.boiler_dhw_nrgconscomp` (8319 kWh) geteilt durch
`sensor.boiler_dhw_startshp` (2649 Starts) ergibt 3.14 kWh
(`../WW-Steuerung/CSV/harvest_2026-09-08-20-33-39.csv`). Das ist ein
Lebenszeit-Mittelwert, kein saisonaler Wert; im Winter dürfte der Bedarf
höher liegen.
→ Der Wert ist im Konfigurationsdialog frei einstellbar.

**B4. Wirkungsgrad und Kapazität sind Vorgabewerte, keine Messwerte.**
`sensor.marstek_venus_modbus_gesamt_roundtrip_effizienz` war im Snapshot
`unknown`. Verwendet wird deshalb der einstellbare Vorgabewert 0.90; die
Kapazität 5.12 kWh entspricht dem Marstek Venus E laut Herstellerangabe.
→ Sobald der Sensor liefert, kann der Wert im Dialog nachgezogen werden.

**B5. Kein `ha core check_config` und kein `pytest`-Lauf in dieser Umgebung
möglich.**
Auf dem Entwicklungsrechner ist kein nutzbarer Python-Interpreter installiert
(nur die Microsoft-Store-Platzhalter), und es stand keine laufende
Home-Assistant-Instanz zur Verfügung. Die Tests in `tests/` wurden geschrieben,
aber **nicht ausgeführt**. Die in `strom_v1_quality_report.md` beschriebenen
statischen Prüfungen ersetzen das nicht.
→ **Vor der ersten Nutzung** die Integration installieren, Home Assistant neu
starten und das Protokoll auf Fehler prüfen; anschliessend `pytest` in einer
Umgebung mit `requirements-test.txt` laufen lassen.

**B6. Die tatsächliche Home-Assistant-Version des Anwenders ist nicht bekannt.**
`hacs.json` fordert mindestens 2025.7.0, weil die Integration die
`ai_task`-Plattform nutzt und die Zielanlage `ai_task.claude_ai_task` besitzt.
Ausserdem werden `entry.runtime_data` (ab 2024.11) und die `type`-Alias-Syntax
(Python 3.12) verwendet.
→ Falls beim Laden ein Importfehler auftritt: exakte Fehlermeldung melden.

**B7. Kein Preis-Array mit voller zeitlicher Auflösung verfügbar.**
Die Tibber-Integration stellt keine Entity mit dem vollständigen
15-Minuten-Preisverlauf bereit; `sensor.home_diagramm_datenexport` trug im
Export keine Datenattribute. Gearbeitet wird deshalb mit den Fenstern aus
`periods` und den Punktwerten. Für die Fensterwahl reicht das; eine
echte Optimierung über alle Intervalle wäre feiner.

## Teil C – Bewusst nicht umgesetzt

**C1. Keine Ansteuerung des Speichers.** Siehe A2. Sobald belegt ist, welche
Entity den Lade-/Entlademodus setzt und welche Werte sie annimmt, kann eine
Aktorebene ergänzt werden. Diese Ergänzung ist ausdrücklich abzustimmen,
bevor sie gebaut wird.

**C2. Keine Steuerung von Waschmaschine, Trockner oder Spülmaschine.** Für
diese Geräte existieren zwar schaltbare Steckdosen (`switch.waschmaschine`,
`switch.trockner`, `switch.spuehlmaschine`), ihre Automatisierung war aber
nicht Teil der Aufgabenstellung. Sie werden nur als Leistungsmesswert geführt.

**C3. Keine Entladesteuerung.** Die Aufgabenstellung betrifft ausschliesslich
die Ladung. Wann der Speicher entlädt, bleibt der Geräteautomatik überlassen.

**C4. Keine Koordination mit `ww_v3` über gemeinsame Sperren.** Beide Systeme
lesen dieselben Preisfenster und kommen dadurch zu konsistenten
Zeitfenstern, es gibt aber keinen expliziten Abgleich. Solange die
Integration keinen Aktor bedient, kann daraus kein Konflikt entstehen.
→ Vor Einführung einer Aktorebene ist dieser Punkt zu klären.
