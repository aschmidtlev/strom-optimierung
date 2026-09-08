# strom_v1 – Qualitätsbericht

Stand: 09.09.2026. Dieser Bericht hält fest, was tatsächlich geprüft wurde –
und ebenso deutlich, was **nicht** geprüft werden konnte.

## 1. Durchgeführte Prüfungen

### 1.1 Existenzabgleich aller referenzierten Entities

Alle 20 im Code vorkommenden Entity-IDs wurden **einzeln** gegen die
Snapshots im Ordner `csv/` geprüft, nicht stichprobenartig. Ergebnis: 20 von
20 belegt, keine davon `unavailable` oder `unknown`.

| Prüfung | Ergebnis |
|---|---|
| Entity-IDs im Code gefunden | 20 |
| davon im Snapshot belegt | 20 |
| davon mit unbrauchbarem Zustand | 0 |

Die Zuordnung Entity → Quellzeile steht vollständig in
`strom_v1_entity_mapping.md`.

### 1.2 Keine Referenz auf ausgefallene oder unverifizierte Quellen

Volltextsuche nach `marstek` über `custom_components/`: vier Treffer,
**ausschliesslich Kommentarzeilen** (`config_flow.py:88`, `const.py:27`,
`const.py:53`, `const.py:57`). Keine Marstek-Entity wird im Code referenziert
oder als Vorschlagswert gesetzt.

Ebenfalls geprüft und nicht referenziert: `sensor.gesamtleistung_haushalt`
(laut `../WW-Steuerung/ww_v3_open_questions.md` B6 fragwürdig),
`sensor.marstek_venus_modbus_batterieleistung` (Vorzeichenkonvention
unverifiziert), sämtliche `ww_v1_8_*`- und `ww_v2_*`-Entities (im Snapshot
durchgängig `unavailable`).

### 1.2b Existenzabgleich der Dashboard-Referenzen

`strom_v1_dashboard.yaml` referenziert 83 Entities. Alle wurden maschinell
gegen die Snapshots beziehungsweise gegen die von der Integration selbst
erzeugten Entities geprüft.

| Prüfung | Ergebnis |
|---|---|
| Referenzen im Dashboard | 83 |
| davon Entities der Integration | 13 |
| davon im Snapshot belegt | 70 |
| nicht auflösbar | 0 |

Zwei der belegten Entities stehen im Snapshot auf `unavailable`
(`sensor.marstek_venus_modbus_soc_batterie`,
`sensor.marstek_venus_modbus_batterieleistung`). Sie erscheinen ausschliesslich
in auskommentierten Zeilen sowie – im Fall des Ladestands – innerhalb eines
`{% if %}`-Zweigs, der nur greift, wenn die Modbus-Verbindung tatsächlich
`on` ist. Es wird also nie ein unbelegter Wert angezeigt.

Ebenfalls geprüft: die Struktur des Dashboards (4 Ansichten, 24 Karten, keine
Tabulatoren, keine doppelten Kartentitel, keine leeren Blockskalare).

### 1.3 Eindeutigkeit von IDs

| Prüfung | Ergebnis |
|---|---|
| Entity-Schlüssel (Basis der `unique_id`) | 13, alle eindeutig |
| Konfigurationsschlüssel `CONF_*` | keine doppelten Werte |

Die `unique_id` wird als `{entry_id}_{key}` gebildet und ist damit auch bei
mehreren Einträgen kollisionsfrei. Der Konfigurationsdialog erlaubt über
`_abort_if_unique_id_configured()` ohnehin nur einen Eintrag.

### 1.4 JSON-Gültigkeit und Übersetzungsabdeckung

| Datei | Gültiges JSON | Kein BOM | Alle 13 Entity-Schlüssel übersetzt |
|---|---|---|---|
| `manifest.json` | ja | ja | – |
| `hacs.json` | ja | ja | – |
| `strings.json` | ja | ja | ja |
| `translations/de.json` | ja | ja | ja |
| `translations/en.json` | ja | ja | ja |

Die BOM-Spalte ist kein Selbstzweck: beim Nachtragen des Schlüssels
`netzleistung` hatte eine PowerShell-Ersetzung allen drei Dateien ein BOM
vorangestellt und zusätzlich die Umlaute in `de.json` doppelt kodiert
(31 Zeilen, `HÃ¶chst` statt `Höchst`). Beides wurde bemerkt und behoben,
die Dateien wurden neu geschrieben und byteweise gegengeprüft.

### 1.5 Beleg für die Netzzähler-Zuordnung

Dass der Shelly Pro 3EM den Netzbezug misst, wurde nicht angenommen, sondern
gegengerechnet: die Phasensumme des Snapshots vom 29.08.2026 (699.9 W) stimmt
exakt mit `sensor.evu_leistung` (699.871 W) desselben Zeitpunkts überein. Im
Snapshot vom 08.09.2026 ergibt die Summe 665.3 W gegenüber
`sensor.tibber_pulse_home_energie` mit 670 W bei PV = 0.

### 1.6 Beim Testschreiben gefundener und behobener Logikfehler

Die erste Fassung von `calculate_target_soc()` setzte den Ziel-Ladestand auf
`min_soc` plus den angekündigten Bedarf. Ohne angekündigten Großverbraucher
ergab das einen Ziel-Ladestand gleich dem Mindest-Ladestand – **Anforderung 1
(Vorladen bei Niedrigpreisphasen) hätte damit nie ausgelöst.** Der Fehler
fiel beim Schreiben von `test_cheap_window_triggers_price_charging` auf.

Korrigiert: Ausgangswert ist jetzt der Höchst-Ladestand; begrenzt wird er
allein durch die PV-Erwartung, und diese Begrenzung darf den Bedarf eines
angekündigten Verbrauchers nicht unterschreiten. Abgesichert durch
`test_pv_reserve_never_undercuts_announced_load`.

## 2. Nicht durchgeführte Prüfungen

### 2.1 Kein Syntax- oder Testlauf

Auf dem Entwicklungsrechner ist **kein nutzbarer Python-Interpreter**
installiert – `python` und `python3` verweisen auf die
Microsoft-Store-Platzhalter, `py` fehlt, WSL ist nicht verfügbar. Damit gilt:

- Die Python-Dateien wurden **nicht** kompiliert oder importiert.
- Die 26 Testfälle in `tests/test_optimizer.py` wurden **geschrieben, aber
  nicht ausgeführt**.
- Ein Syntaxfehler oder ein falscher Home-Assistant-Importpfad würde sich
  erst beim Laden in der echten Instanz zeigen.

Ersatzweise wurden alle Dateien manuell durchgelesen; dabei wurden drei
Fehler gefunden und behoben: ein Zugriff auf ein nicht existierendes Feld
`data.missing_note`, ein Vergleich in `_merge()`, der nach der Zuweisung nie
zutreffen konnte, und ein `default=None` an optionalen
Auswahlfeldern des Konfigurationsdialogs.

### 2.1b Keine YAML-Prüfung des Dashboards

Auf dem Entwicklungsrechner steht kein YAML-Parser zur Verfügung (kein
Python, kein Node, kein Ruby, kein `powershell-yaml`). `strom_v1_dashboard.yaml`
wurde deshalb **nicht geparst**, sondern nur strukturell geprüft
(Einrückungstiefen, Tabulatoren, Blockskalare, Kartenzahl je Ansicht) und
manuell durchgelesen. Ein Syntaxfehler würde beim Einspielen der
Rohkonfiguration sofort auffallen und liesse sich dort ebenso korrigieren.

### 2.2 Kein `ha core check_config`

Es stand keine laufende Home-Assistant-Instanz zur Verfügung.

### 2.3 Keine Prüfung gegen die echte Home-Assistant-Version

Die tatsächliche Version des Anwenders ist nicht bekannt. `hacs.json` fordert
2025.7.0; verwendet werden `entry.runtime_data`, die `type`-Alias-Syntax und
die `ai_task`-Plattform.

## 3. Verbleibendes Risiko

| Risiko | Auswirkung | Abfederung |
|---|---|---|
| Syntax-/Importfehler | Integration lädt nicht | Fällt beim ersten Start sofort auf, keine Nebenwirkung auf andere Systeme |
| Vorzeichenannahme Netzzähler falsch (B1) | PV-Überschussladung wird nie empfohlen | Keine Fehlsteuerung möglich, da kein Aktor bedient wird |
| Attribut `periods` fehlt oder hat andere Feldnamen | Keine Preisfenster, Empfehlung bleibt `idle` | Wird über `binary_sensor.*_datenbasis_unvollstaendig` gemeldet |
| Vorgabewerte für Kapazität, Wirkungsgrad, Warmwasserbedarf ungenau | Ersparnisschätzung ungenau | Alle drei im Dialog einstellbar |
| YAML-Syntaxfehler im Dashboard | Rohkonfiguration lässt sich nicht speichern | Fällt beim Einspielen sofort auf, betrifft die Integration nicht |
| `power-flow-card-plus` fehlt oder ändert seine Konfigurationssyntax | Flow-Karte meldet einen Fehler | Die native Karte „Leistungsbilanz" direkt darunter zeigt dieselben Werte |
| Attribut `letzte_entscheidungen` wächst | Grösseres Zustandsattribut in der Datenbank | Auf fünf Einträge begrenzt, neuer Eintrag nur bei inhaltlicher Änderung |

**Das grösste Risiko dieser Version ist ausdrücklich kein Steuerungsrisiko.**
Die Integration setzt keinen Schaltbefehl ab; der einzige aufgerufene Dienst
ist `ai_task.generate_data`, der Text erzeugt.

## 4. Empfohlene Schritte vor der Nutzung

1. Integration installieren, Home Assistant neu starten, Protokoll auf
   Einträge von `custom_components.strom_optimierung` prüfen.
2. `pytest` in einer Umgebung mit `requirements-test.txt` ausführen.
3. Einige Tage den Verlauf von `sensor.strom_optimierung_empfehlung`
   beobachten, insbesondere ob `charge_pv` bei Sonne überhaupt auftritt
   (Prüfung von B1).
