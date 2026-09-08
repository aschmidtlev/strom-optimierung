# strom_v1 – Bestandsaufnahme und Architekturentscheidung

Stand: 09.09.2026. Analysierte Quellen:

- `csv/` – zwölf Entity-Snapshots vom 08.09.2026, 23:49–00:15 Uhr
  (Developer-Tools-Export der Zielanlage)
- `../WW-Steuerung/` – Nachbarprojekt `ww_v3`, vollständige Dokumentation
  und `ww_v3_package.yaml` (2017 Zeilen)
- `../CLAUDE_INTEGRATION_PROMPT.md` – Arbeitsleitplanken des Anwenders

Keine dieser Dateien wurde verändert.

## 1. Ausgangslage

Der Projektordner enthielt zu Beginn ausschliesslich `csv/` – keinen Code,
kein README, kein Git-Repository. Das Zielrepository
`github.com/aschmidtlev/strom-optimierung` war nicht ausgecheckt.

Im Nachbarordner liegt jedoch ein aktives, produktives Projekt: die
Warmwassersteuerung `ww_v3`, ein **reines YAML-Package** mit gewachsener
Dokumentationsstruktur. Es referenziert dieselben Tibber-Preis-, PV- und
Marstek-Quellen, die auch diese Aufgabe benötigt.

Daraus ergab sich der erste Klärungsbedarf: die Aufgabenstellung beschreibt
eine HACS-Python-Integration, der reale Bestand des Haushalts ist ein
YAML-Package. Der Anwender hat sich für die **Python-Integration**
entschieden (siehe `strom_v1_open_questions.md`, A1).

## 2. Datenlage je Anforderung

| Anforderung | Datenlage | Bewertung |
|---|---|---|
| Preisfenster | `periods`-Attribut zweier Tibber-Zeitraum-Sensoren, mit Start, Ende, Mittel-, Min- und Maxpreis, für heute und morgen | **tragfähig** – die wertvollste Quelle im gesamten Snapshot |
| PV-Prognose | zwei Forecast.Solar-Instanzen, je Zeithorizont ein Sensorpaar | **tragfähig** als Summe |
| PV-Ist | SMA STP10.0-3AV-40, Gesamtleistung und beide Strings | **tragfähig** |
| Netzbezug/-einspeisung | Shelly Pro 3EM, drei Phasenleistungen | **tragfähig**, Vorzeichenkonvention offen (B1) |
| Speicher-Ladestand | Marstek Venus, Modbus | **ausgefallen** – alle 22 Entities `unavailable`/`unknown` |
| Speicher-Steuerung | keine belegte Entity | **nicht vorhanden** |
| Angekündigte Großverbraucher | `sensor.ww_v3_naechster_bestpreis_start` | **tragfähig** |
| KI | `ai_task.claude_ai_task` | **vorhanden** |

## 3. Der ausschlaggebende Befund: keine Steuer-Entity

`binary_sensor.marstek_venus_modbus_modbus_verbindung` steht auf `off`, und
sämtliche Marstek-Sensoren sind `unavailable` oder `unknown`. Der einzige
denkbare Steuerkandidat, `select.marstek_venus_modbus_benutzer_modus`, steht
ebenfalls auf `unknown` – seine Optionsliste ist damit unbekannt. Eine
`number`-Entity für einen Lade- oder Entladesollwert existiert in **keinem**
der vorliegenden Snapshots.

Zusätzlich weisen `update.marstek_local_api_update` und
`update.marstek_venus_energy_manager_update` darauf hin, dass zwei weitere
Marstek-Integrationen installiert sind. Sie liefern in keinem Snapshot
Entities.

Damit war die Kernlogik nicht anschliessbar, ohne eine Entity-ID oder eine
Optionsliste zu raten. Der Anwender hat entschieden, zunächst **nur die
Entscheidungs- und Anzeigeebene** zu bauen (A2).

## 4. Warum das die richtige Reihenfolge ist

Die Trennung hat über die Sicherheitsfrage hinaus einen praktischen Nutzen:
die Entscheidungslogik lässt sich vollständig beobachten, während der
Speicher noch nicht angeschlossen ist. Ob die Empfehlungen plausibel sind,
zeigt sich am Verlauf von `sensor.*_empfehlung` über einige Tage – lange
bevor ein Schaltbefehl Schaden anrichten könnte. Die Aktorebene lässt sich
später ergänzen, ohne die Entscheidungslogik erneut anzufassen: `decide()`
liefert bereits Aktion, Ziel-Ladestand, Zeitfenster und Leistung.

## 5. Aufbau

`optimizer.py` enthält die gesamte Entscheidungslogik und importiert bewusst
**nichts** aus Home Assistant. Dadurch ist sie ohne laufende Instanz
testbar – was in dieser Umgebung der einzig mögliche Prüfweg war.
`coordinator.py` liest die Zustände und baut daraus die Eingangsdaten,
`ai_advisor.py` kapselt den optionalen KI-Pfad, die Plattformen
`sensor`/`binary_sensor` machen das Ergebnis sichtbar.

## 6. Abgrenzung zu ww_v3

`ww_v3` bleibt unverändert. Diese Integration liest lediglich zwei seiner
Sensoren (`sensor.ww_v3_naechster_bestpreis_start` als angekündigte Last,
`sensor.ww_v3_hausverbrauch_berechnet` als Ersatzpfad für die
Überschussrechnung) und schreibt nichts zurück. Da kein Aktor bedient wird,
kann kein Steuerungskonflikt entstehen – siehe
`strom_v1_open_questions.md`, C4.
