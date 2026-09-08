# Strom-Optimierung

Home-Assistant-Integration, die für einen Hausbatteriespeicher entscheidet,
**wann** und **wie weit** geladen werden sollte – auf Basis dynamischer
Strompreise, der PV-Prognose beider Anlagen und angekündigter
Großverbraucher.

> **Diese Version schaltet nichts.** Sie liefert Empfehlung, Ziel-Ladestand,
> Ladefenster und Begründung als Entities. Grund: der Marstek Venus war bei
> der Entwicklung hardwareseitig ausgefallen, und ohne belegte Steuer-Entity
> wäre jede Schaltlogik geraten gewesen. Die Aktorebene kann ergänzt werden,
> sobald die Steuer-Entities verifiziert sind – siehe
> [offene Fragen](docs/strom_v1_open_questions.md).

## Was die Integration entscheidet

1. **Vorladen bei Niedrigpreisphasen** – laden, solange ein günstiges
   Preisfenster läuft und der später vermiedene Preis den Zyklus trägt.
2. **Antizipatives Laden vor Großverbrauchern** – kündigt die
   Warmwassersteuerung eine Ladung zu einem teuren Zeitpunkt an, wird der
   Speicher im günstigsten davor liegenden Fenster vorgeladen.
3. **PV-Überschussladung** – speist die Anlage ins Netz ein, hat das Vorrang
   vor jeder Preisregel.
4. **PV-Prognose beider Anlagen** – ist viel Sonne zu erwarten, wird der
   Ziel-Ladestand gesenkt, damit Kapazität für den Überschuss frei bleibt.
5. **Optionale KI-Entscheidung** – die Regelentscheidung kann einem
   Sprachmodell zur Prüfung vorgelegt werden. Ohne API-Zugang, bei einem
   Fehler oder bei einer unplausiblen Antwort gilt unverändert die Regel.

## Wirtschaftlichkeit

Aus dem Netz zu laden lohnt nur, wenn

    vermiedener Preis > Ladepreis / Wirkungsgrad + Verschleissaufschlag

Mit den Vorgabewerten (Wirkungsgrad 0.90, Aufschlag 2.0 ct/kWh) muss ein
Fenster zu 23 ct/kWh später über 27.8 ct/kWh vermeiden, damit geladen wird.

## Installation

Über HACS als benutzerdefiniertes Repository vom Typ *Integration*:

```
https://github.com/aschmidtlev/strom-optimierung
```

> HACS kann nur auf **öffentliche** Repositories zugreifen. Ist das Repository
> privat, bricht das Hinzufügen mit `GitHub returned 404` ab – dann entweder
> die Sichtbarkeit umstellen oder nach Abschnitt 3 der
> [Installationsanleitung](docs/strom_v1_installation.md) manuell
> installieren.

Danach Home Assistant neu starten und die Integration unter
**Einstellungen → Geräte & Dienste** hinzufügen. Ausführlich in der
[Installationsanleitung](docs/strom_v1_installation.md).

## Voraussetzungen

- Home Assistant 2025.7.0 oder neuer
- Eine Tibber-Preisintegration, deren Zeitraum-Sensoren das Attribut
  `periods` mit den Preisfenstern bereitstellen (Pflicht)
- PV-Prognose, PV-Ist, Netzleistung, Speicher-Ladestand und ein angekündigter
  Großverbraucher sind jeweils optional. Was fehlt, meldet
  `binary_sensor.strom_optimierung_datenbasis_unvollstandig`.

## Bereitgestellte Entities

| Entity | Bedeutung |
|---|---|
| `sensor.strom_optimierung_empfehlung` | `idle`, `charge_pv`, `charge_price`, `charge_anticipatory` oder `hold`; Attribute tragen Begründung, Quelle, Fenster, Ersparnis und die letzten fünf Entscheidungen |
| `sensor.strom_optimierung_ziel_ladestand` | Ziel-Ladestand in Prozent |
| `sensor.strom_optimierung_empfohlene_ladeleistung` | Rechnerische Ladeleistung für das Fenster |
| `sensor.strom_optimierung_netzleistung` | Summe der konfigurierten Phasen als ein Wert; negativ bedeutet Einspeisung |
| `sensor.strom_optimierung_pv_uberschuss` | Erkannter Überschuss |
| `sensor.strom_optimierung_erwarteter_grossverbrauch` | Angekündigte Last im 24-Stunden-Horizont |
| `sensor.strom_optimierung_erwartete_ersparnis` | Geschätzte Ersparnis der Empfehlung |
| `sensor.strom_optimierung_ladefenster_start` / `_ende` | Zeitfenster der Empfehlung |
| `sensor.strom_optimierung_entscheidungsquelle` | `rule`, `ai` oder `ai_fallback` |
| `binary_sensor.strom_optimierung_laden_empfohlen` | An bei jeder Ladeaktion |
| `binary_sensor.strom_optimierung_gunstiges_fenster_aktiv` | An während eines günstigen Fensters |
| `binary_sensor.strom_optimierung_datenbasis_unvollstandig` | An bei fehlenden Eingangswerten; Attribut nennt welche |

## Dashboard

`strom_v1_dashboard.yaml` liefert ein fertiges Lovelace-Dashboard mit vier
Ansichten:

- **Stromfluss** – Flussdiagramm Netz, PV und Haus, dazu die exakten Zahlen
  je Phase und String
- **Entscheidung** – aktuelle Empfehlung im Klartext, **die letzten drei
  Entscheidungen mit vollständiger Begründung**, Ziel-Ladestand, Zeitfenster
- **Preise** – Preis jetzt und Vorschau, günstiges und teures Fenster,
  PV-Prognose beider Anlagen, eine Karte die vorrechnet, ob sich Netzladen
  gerade trägt
- **Diagnose** – fehlende Eingangswerte, Zustand der Quellintegrationen

Einspielen über **Einstellungen → Dashboards → Dashboard hinzufügen →
Rohkonfiguration bearbeiten** und den Dateiinhalt einfügen.

Die einzige HACS-Abhängigkeit ist `power-flow-card-plus` für das
Flussdiagramm. Fehlt die Karte, bleibt das Dashboard vollständig nutzbar –
die native Karte direkt darunter zeigt dieselben Werte.

Der Batteriespeicher fehlt im Flussdiagramm, solange der Marstek keine Daten
liefert. Der fertige Konfigurationsblock zum Nachrüsten steht als Kommentar
an der betreffenden Stelle in der Datei.

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [Bestandsaufnahme](docs/strom_v1_analysis.md) | Datenlage, Architekturentscheidung, warum keine Aktorebene |
| [Entity-Mapping](docs/strom_v1_entity_mapping.md) | Jede referenzierte Entity mit Beleg und Quellzeile |
| [Funktionsmatrix](docs/strom_v1_function_matrix.md) | Anforderung → Umsetzung, Entscheidungsreihenfolge |
| [Installation](docs/strom_v1_installation.md) | Einrichtung, Prüfung, Testbetrieb, Rollback |
| [Offene Fragen](docs/strom_v1_open_questions.md) | Getroffene Annahmen und was zu ihrer Klärung fehlt |
| [Qualitätsbericht](docs/strom_v1_quality_report.md) | Was geprüft wurde – und was nicht |
| [Testplan](docs/strom_v1_testplan.md) | Automatisierte Tests, manuelle Prüfungen, Beobachtung im Betrieb |
| [Änderungsprotokoll](docs/strom_v1_changelog.md) | Versionshistorie |

## Entwicklung

```bash
pip install -r requirements-test.txt
pytest
```

Die gesamte Entscheidungslogik liegt in
`custom_components/strom_optimierung/optimizer.py` und importiert bewusst
nichts aus Home Assistant. Sie ist dadurch ohne laufende Instanz testbar.
