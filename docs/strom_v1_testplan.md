# strom_v1 – Testplan

## Teil A – Automatisierte Tests

`tests/test_optimizer.py` (26 Fälle) prüft `optimizer.py`, das bewusst keine
Home-Assistant-Importe enthält und daher ohne laufende Instanz lauffähig ist.
Die Zahlenwerte stammen aus dem Snapshot vom 08.09.2026, damit die Fälle die
reale Preisstruktur abbilden.

`tests/test_config_flow.py` (10 Fälle) prüft den Konfigurationsdialog,
schwerpunktmässig den Bau der Schemata. Ein Selector mit unzulässiger
Konfiguration wirft erst beim Anzeigen des Formulars und erscheint dem
Anwender nur als „Unknown error occurred" – ohne jeden Hinweis auf die
Ursache. Genau das ist einmal passiert, siehe `strom_v1_changelog.md`.

**Status: geschrieben, nicht ausgeführt** – siehe
`strom_v1_open_questions.md`, B5.

| Bereich | Fälle | Prüft |
|---|---|---|
| Überschusserkennung | 4 | Einspeisung wird als Überschuss gewertet, Netzbezug nicht; Ersatzpfad PV minus Hausverbrauch; unbekannt ohne jede Quelle |
| Preisfenster | 4 | Preis zu einem Zeitpunkt aus dem passenden Fenster, Rückfall auf den Mittelwert, günstigstes Fenster vor einer Frist, Fenster nach der Frist werden ignoriert |
| Wirtschaftlichkeit | 1 | Verlust- und Verschleisskorrektur an der Entscheidungsschwelle |
| Ziel-Ladestand | 5 | Höchstwert ohne PV-Erwartung, Absenkung bei hoher PV-Prognose, Vorrang des angekündigten Bedarfs, abschaltbare PV-Reserve, Deckelung am Höchstwert |
| Entscheidungen | 12 | Alle fünf Aktionen, Rangfolge PV vor Preis, voller Speicher, fehlende Preisdaten, fehlender Ladestand, Horizontgrenze |
| Dialogschemata | 6 | Alle vier Schemata bauen mit und ohne Vorbelegung; einheitenloses Zahlenfeld setzt `unit_of_measurement` nicht; Pflichtfelder greifen; plausible Eingabe wird angenommen |
| Vorschlagswerte | 2 | Alle Vorschläge sind gültige Entity-IDs; der Speicher-Ladestand wird bewusst nicht vorgeschlagen |
| Eingabebereinigung | 2 | Leere Auswahlfelder entfallen, die Null bleibt erhalten |

## Teil B – Manuelle Prüfungen nach der Installation

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| B1 | Integration installieren, Home Assistant neu starten | Kein Fehler im Protokoll unter `custom_components.strom_optimierung` |
| B2 | Konfigurationsdialog durchlaufen | Alle vier Schritte lassen sich abschliessen, Vorschlagswerte sind sichtbar |
| B3 | Mindest-Ladestand über den Höchst-Ladestand setzen | Dialog weist mit „Der Mindest-Ladestand muss unter dem Höchst-Ladestand liegen" zurück |
| B4 | KI-Pfad einschalten ohne `ai_task`-Entity | Dialog weist mit „Für den KI-Pfad muss eine ai_task-Entity ausgewählt werden" zurück |
| B5 | `sensor.strom_optimierung_empfehlung` prüfen | Zeigt eine der fünf Aktionen, nicht `unavailable` |
| B6 | Attribut `erlaeuterung` lesen | Enthält einen verständlichen deutschen Satz mit konkreten Zahlen |
| B7 | `binary_sensor.strom_optimierung_datenbasis_unvollstaendig` prüfen | Solange der Marstek ausgefallen ist: *an*, Attribut `fehlende_daten` nennt „Speicher-SoC" |
| B8 | Integration zweimal hinzufügen | Zweiter Versuch wird mit „bereits eingerichtet" abgebrochen |
| B9 | Über **Konfigurieren** die Kapazität ändern | Integration lädt neu, `sensor.strom_optimierung_ziel_soc` rechnet mit dem neuen Wert |
| B10 | Diagnose herunterladen | Enthält Konfiguration, Eingangswerte, letzte Entscheidung und die Historie |
| B11 | Attribut `letzte_entscheidungen` der Empfehlungs-Entity prüfen | Nach dem ersten Lauf ein Eintrag; nach einigen Minuten ohne Änderung **weiterhin** ein Eintrag, keine Duplikate |
| B12 | Warten, bis sich die Empfehlung ändert | Ein zweiter Eintrag erscheint, der ältere rutscht nach hinten; höchstens fünf Einträge |

## Teil B2 – Dashboard

`strom_v1_dashboard.yaml` einspielen (Einstellungen → Dashboards → neues
Dashboard → Rohkonfiguration ersetzen).

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| B20 | Ansicht **Stromfluss** öffnen | Flow-Karte zeigt Netz, PV und Haus mit Werten |
| B21 | `power-flow-card-plus` testweise deaktivieren | Karte meldet einen Fehler, die Ansicht bleibt sonst vollständig nutzbar – die Karte „Leistungsbilanz" darunter zeigt dieselben Zahlen |
| B22 | Karte **Speicherstatus** lesen | Solange der Marstek aus ist: Hinweistext statt Ladestand, ohne Fehlermeldung |
| B23 | Ansicht **Entscheidung** öffnen | Kopfkarte zeigt Aktion, Begründung und Erläuterung im Klartext |
| B24 | Karte **Letzte drei Entscheidungen** lesen | Bis zu drei Einträge mit Zeitpunkt, Aktion, Begründung und Erläuterung; direkt nach der Installation der Hinweis „Noch keine Entscheidung aufgezeichnet" |
| B25 | Ansicht **Preise** öffnen | Karte „Lohnt sich Netzladen gerade?" rechnet die Schwelle aus und nennt sie |
| B26 | Ansicht **Diagnose** öffnen | Karte „Datenbasis" listet die fehlenden Eingangswerte auf |
| B27 | Alle vier Ansichten auf Fehlerkarten durchsehen | Keine Karte meldet „Entity nicht gefunden" |

## Teil C – Beobachtung im Betrieb

Diese Punkte lassen sich nur über mehrere Tage prüfen. Sie sind der
eigentliche Wirksamkeitsnachweis, bevor über eine Aktorebene gesprochen wird.

| # | Beobachtung | Bewertung |
|---|---|---|
| C1 | Tritt `charge_price` in den erkennbar günstigen Stunden auf? | Bestätigt Anforderung 1 |
| C2 | Erscheint `charge_anticipatory` vor der von `ww_v3` angekündigten Warmwasserladung? | Bestätigt Anforderung 2 |
| C3 | Springt die Empfehlung an sonnigen Tagen auf `charge_pv`? | Bestätigt Anforderung 3 **und** die Vorzeichenannahme B1. Tritt sie nie auf, ist B1 zu prüfen. |
| C4 | Sinkt `sensor.strom_optimierung_ziel_soc` vor einem sonnigen Folgetag? | Bestätigt Anforderung 4 |
| C5 | Weicht die KI bei aktiviertem Pfad von der Regel ab, und ist die Begründung nachvollziehbar? | Bewertet Anforderung 5 |
| C6 | Steht `sensor.strom_optimierung_entscheidungsquelle` dauerhaft auf `ai_fallback`? | Deutet auf ein Problem mit der `ai_task`-Entity hin; Protokoll prüfen |

## Teil D – Bei Wiederkehr der Marstek-Verbindung

| # | Schritt |
|---|---|
| D1 | Neuen CSV-Export aller `marstek`-Entities erstellen, inklusive der Attribute von `select.marstek_venus_modbus_benutzer_modus` (dort steht die Optionsliste) |
| D2 | `sensor.marstek_venus_modbus_soc_batterie` im Dialog unter **Konfigurieren** als Ladestand eintragen |
| D3 | Prüfen, dass `binary_sensor.strom_optimierung_datenbasis_unvollstaendig` auf *aus* geht |
| D4 | Erst danach über eine Aktorebene sprechen – siehe `strom_v1_open_questions.md`, C1 |
