# strom_v1 – Änderungsprotokoll

## 0.1.3 – 09.09.2026

Reine Dokumentationsversion. **Am Integrationscode ändert sich nichts** – wer
0.1.2 installiert hat, gewinnt durch das Update funktional nichts.

- `strom_v1_open_questions.md` erklärt unter **B8**, warum diese Integration
  keine Nulleinspeisungs- beziehungsweise Eigenverbrauchsregelung leistet und
  auch nicht leisten soll: das ist eine Regelungsaufgabe im Sekundentakt und
  gehört in den Speicher, während diese Integration im Minutentakt plant.
- Dort ebenfalls festgehalten sind die beiden Folgen daraus, die man kennen
  muss: sobald der Speicher den Eigenverbrauch selbst regelt, erreicht kein
  Überschuss mehr den Zähler – die PV-Überschusserkennung wird damit blind
  und `charge_pv` löst nicht mehr aus. Und „Vorladen in Niedrigpreisphasen"
  erzeugt bewusst Netzbezug, steht also im Zielkonflikt zu „Netzbezug gegen
  null".
- **C1** hält fest, dass eine spätere Aktorebene eine zeitlich begrenzte
  Übersteuerung werden soll, keine Regelung: Eigenverbrauch als
  Normalzustand, erzwungenes Netzladen nur im günstigen Fenster, danach
  zurück.

## 0.1.2 – 09.09.2026

Der KI-Pfad war nach der Einrichtung nicht mehr erreichbar.

### Behoben

- **Der Optionen-Dialog zeigte nur die Grenzwerte.** Quell-Entities,
  Großverbraucher und der gesamte KI-Pfad liessen sich nach dem ersten
  Speichern nicht mehr ändern – die `ai_task`-Entity war damit dauerhaft
  festgelegt. Die Optionen bieten jetzt ein Menü über dieselben vier
  Bereiche wie die Einrichtung.
- Ein überflüssiger Sonderfall für den KI-Schalter im Optionen-Dialog wurde
  wieder entfernt: `_strip_empty()` entfernt `False` gar nicht, der Wert kam
  ohnehin durch. Ein Test hält das jetzt fest.

### Hinzugefügt

- `switch.strom_optimierung_ki_entscheidung_nutzen` – schaltet den KI-Pfad im
  laufenden Betrieb ein und aus, ohne die Integration neu zu laden. Der
  Zustand übersteht einen Neustart über `RestoreEntity`; die Option im Dialog
  legt nur noch den Startwert fest, falls keine frühere Aufzeichnung
  vorliegt. Attribute nennen die befragte `ai_task`-Entity und ob der
  Schalter überhaupt wirksam ist.
- Dashboard: Karte **KI-Pfad** in der Ansicht *Entscheidung*, dazu eine
  Hinweiskarte, die nur bei `ai_fallback` erscheint und die möglichen
  Ursachen nennt.
- Drei weitere Testfunktionen in `tests/test_config_flow.py` (jetzt 12), darunter eine, die
  sicherstellt, dass jeder Einrichtungsschritt auch in den Optionen
  erreichbar bleibt.

### Offen

Die Entity-ID `switch.strom_optimierung_ki_entscheidung_nutzen` ist nach der
bekannten Regel abgeleitet, aber noch nicht gegen einen Snapshot belegt – der
vorliegende Vollexport entstand vor dieser Version. Der Name enthält keine
Umlaute, die Ableitung ist daher eindeutig; zu bestätigen ist sie trotzdem,
siehe `strom_v1_testplan.md`, B13.

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
- Neue Testdatei `tests/test_config_flow.py` mit neun Testfunktionen. Sie baut alle
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
- **Vier Entity-IDs im Dashboard und in der Dokumentation waren falsch.** Sie
  waren aus den Schlüsseln im Code abgeleitet worden. Home Assistant bildet
  die entity_id aber aus dem *angezeigten Namen* und transliteriert dabei
  Umlaute (`ü` zu `u`, `ä` zu `a`). Korrigiert: `ziel_soc` zu
  `ziel_ladestand`, `pv_ueberschuss` zu `pv_uberschuss`,
  `guenstiges_fenster_aktiv` zu `gunstiges_fenster_aktiv`,
  `datenbasis_unvollstaendig` zu `datenbasis_unvollstandig`. Der
  Integrationscode ist davon nicht betroffen – nur `strom_v1_dashboard.yaml`,
  `README.md` und zwei Dokumente.
- `strom_v1_entity_mapping.md` führt die eigenen Entities jetzt mit ihrer
  tatsächlichen entity_id, verifiziert gegen einen Vollexport der laufenden
  Instanz.

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
