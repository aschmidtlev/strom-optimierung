# strom_v1 – Änderungsprotokoll

## 0.1.1 – 09.09.2026

Fehlerkorrektur nach der ersten Installation auf der Zielanlage.

- **Konfigurationsdialog brach im Schritt „PV und Netz" mit „Unknown error
  occurred" ab.** Ursache war nicht dieser Schritt, sondern das Schema des
  darauf folgenden: `_number()` setzte `unit_of_measurement=None`, wenn ein
  Zahlenfeld keine Einheit hat. Das Selector-Schema von Home Assistant prüft
  diesen Schlüssel gegen `str` und weist `None` zurück; die Ausnahme trat
  beim Bauen des nächsten Formulars auf und erschien deshalb am vorherigen
  Schritt. Betroffen war allein der Wirkungsgrad – das einzige einheitenlose
  Feld. Der Schlüssel wird jetzt weggelassen statt auf `None` gesetzt.
- Neue Testdatei `tests/test_config_flow.py` mit zehn Fällen. Sie baut alle
  vier Schemata mit und ohne Vorbelegung und prüft gezielt, dass ein
  einheitenloses Zahlenfeld den Schlüssel `unit_of_measurement` nicht setzt.
  Damit fällt diese Fehlerklasse künftig im Test auf statt erst im Dialog.
- README und Installationsanleitung halten fest, dass HACS ein **öffentliches**
  Repository braucht. Das Hinzufügen war mit `GitHub returned 404`
  gescheitert, weil das Repository privat ist – GitHub antwortet dort
  bewusst mit 404 statt 403.
- **Neue Version wurde in HACS nicht angeboten.** HACS ermittelt die Version
  eines Custom Repositories aus den GitHub-Releases, nicht aus
  `manifest.json`. Das Repository hatte keine Releases, HACS verfolgte
  deshalb nur den Standardbranch. Ein blosser Git-Tag hilft ebenfalls nicht:
  GitHub erzeugt daraus kein Release.
- `.github/workflows/release.yml` legt nun zu jedem gepushten Tag ein Release
  an, mit dem eingebauten Runner-Token und der dort vorinstallierten
  GitHub-CLI – ohne eigenes Geheimnis und ohne fremde Action. Damit kann ein
  Release nicht mehr vergessen werden.

## 0.1.0 – 09.09.2026

Erste Fassung. Neuentwicklung ohne Vorgängerversion in diesem Repository.

### Warum diese Fassung so aussieht

Die Aufgabenstellung beschreibt eine Integration, die den Marstek-Venus-
Speicher **steuert**. Der Entity-Snapshot zeigte jedoch, dass der Speicher
hardwareseitig ausgefallen ist: `binary_sensor.marstek_venus_modbus_modbus_verbindung`
steht auf `off`, alle 22 Marstek-Sensoren sind `unavailable` oder `unknown`,
und die Optionsliste des einzigen denkbaren Steuerkandidaten
`select.marstek_venus_modbus_benutzer_modus` ist damit unbekannt.

Der Anwender hat entschieden, zunächst nur die Entscheidungs- und
Anzeigeebene zu bauen. Diese Fassung setzt deshalb **keinen Schaltbefehl**
ab. Sie ist vollständig nutzbar: sie sagt, was zu tun wäre, und begründet es.

### Hinzugefügt

- Python-`custom_component` `strom_optimierung`, über HACS als Custom
  Repository installierbar (`hacs.json`, `manifest.json`)
- Vierstufiger Konfigurationsdialog mit Vorschlagswerten aus dem
  Entity-Snapshot; nachträgliche Änderung der Grenzwerte über die Optionen
- `optimizer.py` – regelbasierte Entscheidung, bewusst ohne
  Home-Assistant-Importe und dadurch ohne laufende Instanz testbar
- `coordinator.py` – liest die Quellzustände im Minutentakt, wertet das
  Attribut `periods` der Tibber-Zeitraum-Sensoren aus
- `ai_advisor.py` – optionaler KI-Pfad über `ai_task.generate_data`, mit
  Wertebereichsprüfung der Antwort und Rückfall auf die Regelentscheidung
- Zehn Sensoren und drei Binärsensoren, deutsch und englisch übersetzt
- `sensor.*_netzleistung` – fasst die einzeln konfigurierten Phasen des
  Netzzählers zu einem Wert zusammen. Nötig, weil Flow-Karten eine einzelne
  Netzleistungs-Entity erwarten, der Shelly Pro 3EM aber drei getrennte
  Phasensensoren liefert.
- Entscheidungshistorie: die letzten fünf Entscheidungen samt Begründung im
  Attribut `letzte_entscheidungen` der Empfehlungs-Entity. Ein Eintrag
  entsteht nur bei einer inhaltlichen Änderung, nicht bei jedem Lauf.
- `strom_v1_dashboard.yaml` – Lovelace-Dashboard mit vier Ansichten:
  Stromfluss, Entscheidung (inklusive der letzten drei Entscheidungen mit
  Erläuterung), Preise und Prognose, Diagnose
- Diagnose-Download mit Eingangswerten und letzter Entscheidung
- 26 Testfälle gegen die Preisstruktur des realen Snapshots
- Dokumentation in der Struktur des Nachbarprojekts `ww_v3`

### Während der Entwicklung behoben

- **Ziel-Ladestand blieb ohne angekündigten Verbraucher beim Mindestwert.**
  Damit hätte Anforderung 1 (Vorladen bei Niedrigpreisphasen) nie ausgelöst.
  Ausgangswert ist jetzt der Höchst-Ladestand, begrenzt allein durch die
  PV-Erwartung. Gefunden beim Schreiben der Tests.
- **Ost/West als Konfigurationsachse entfernt.** Die Zuordnung liess sich aus
  den Daten nicht belegen. Die Prognosewerte beider Anlagen werden jetzt je
  Zeithorizont summiert – damit entfällt die Annahme vollständig.
- Zugriff auf ein nicht existierendes Feld `data.missing_note` im KI-Prompt
- Vergleich in `_merge()`, der nach der Zuweisung nie zutreffen konnte
- `default=None` an optionalen Auswahlfeldern durch das übliche
  `suggested_value`-Muster ersetzt
- Binärsensor `datenbasis_vollstaendig` in `datenbasis_unvollstaendig`
  umbenannt: mit der Geräteklasse `problem` bedeutet *an* eine Störung, der
  alte Name sagte das Gegenteil
- **Zerstörte Umlaute in `translations/de.json` repariert.** Eine Ersetzung
  über PowerShell `Set-Content -Encoding utf8` hatte die Datei doppelt
  kodiert (31 Zeilen mit `HÃ¶chst` statt `Höchst`) und allen drei
  JSON-Dateien ein BOM vorangestellt, das Home Assistant beim Einlesen
  gestört hätte. Alle drei Dateien wurden ohne BOM neu geschrieben und
  gegengeprüft.

### Bewusst nicht enthalten

- Jede Form von Geräteansteuerung (siehe oben)
- Steuerung von Waschmaschine, Trockner, Spülmaschine – deren schaltbare
  Steckdosen existieren, waren aber nicht Teil der Aufgabenstellung
- Entladesteuerung
- Referenzen auf `sensor.gesamtleistung_haushalt` und
  `sensor.marstek_venus_modbus_batterieleistung`, deren Bedeutung
  beziehungsweise Vorzeichenkonvention laut
  `../WW-Steuerung/ww_v3_open_questions.md` B6 unverifiziert ist

### Bekannte Einschränkungen

Siehe `strom_v1_open_questions.md`. Die wichtigsten: die Vorzeichenkonvention
des Netzzählers ist nicht belegt (B1), und weder `pytest` noch
`ha core check_config` konnten in der Entwicklungsumgebung ausgeführt werden
(B5).
