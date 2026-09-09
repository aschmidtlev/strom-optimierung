# strom_v1 – Funktionsmatrix

Zuordnung der Anforderungen aus der Aufgabenstellung zur Umsetzung im Code.

| # | Anforderung | Umsetzung | Fundstelle |
|---|---|---|---|
| 1 | Vorladen bei Niedrigpreisphasen | Liegt der aktuelle Zeitpunkt in einem Fenster aus `periods` des Bestpreis-Sensors und ist Laden wirtschaftlich, lautet die Empfehlung `charge_price`. | `optimizer.decide()`, Regel 4 |
| 2 | Antizipatives Laden vor Großverbrauchern | Der von `ww_v3` angekündigte Warmwasserstart wird als `ExpectedLoad` geführt. Liegt der erwartete Preis zu diesem Zeitpunkt über dem verlustkorrigierten Ladepreis, wird im günstigsten davor liegenden Fenster geladen: `charge_anticipatory`. | `optimizer.decide()`, Regel 3 |
| 3 | PV-Überschussladung | Überschreitet der Überschuss die Schwelle, hat er Vorrang vor jeder Preisregel: `charge_pv` mit Ziel gleich Höchst-Ladestand. | `optimizer.decide()`, Regel 2 |
| 4 | PV-Prognose beider Anlagen einrechnen | Die Prognosewerte beider Anlagen werden je Zeithorizont summiert. Ist viel PV zu erwarten, wird der Ziel-Ladestand abgesenkt, damit Kapazität für den Überschuss frei bleibt. | `optimizer.calculate_target_soc()` |
| 5 | Optionale KI-Entscheidung | Ist der KI-Pfad aktiviert und eine `ai_task`-Entity gewählt, wird die Regelentscheidung dem Modell zur Prüfung vorgelegt. Ohne Aktivierung, ohne Entity, bei Fehler oder bei unplausibler Antwort gilt unverändert die Regelentscheidung. | `ai_advisor.AiAdvisor.refine()` |

## Entscheidungsreihenfolge

Die Regeln greifen in fester Reihenfolge; die erste zutreffende gewinnt.

| Rang | Bedingung | Ergebnis |
|---|---|---|
| 1 | Ladestand hat den Höchstwert erreicht | `hold` |
| 2 | PV-Überschuss über der Schwelle | `charge_pv`, Ziel = Höchst-Ladestand |
| 3 | Kein aktueller Preis verfügbar | `idle` |
| 4 | Angekündigter Großverbraucher, dessen Preis das Laden trägt | `charge_anticipatory`, oder `hold` bis das günstige Fenster beginnt |
| 5 | Günstiges Fenster aktiv und Laden wirtschaftlich | `charge_price`, oder `hold` bei erreichtem Ziel |
| 6 | sonst | `idle`, mit Hinweis auf das nächste Fenster |

## Wirtschaftlichkeitsprüfung

Aus dem Netz zu laden lohnt nur, wenn

    vermiedener Preis > Ladepreis / Wirkungsgrad + Verschleissaufschlag

Mit den Vorgabewerten (Wirkungsgrad 0.90, Aufschlag 2.0 ct/kWh) und dem
günstigen Fenster aus dem Snapshot (23.21 ct/kWh) muss der später vermiedene
Preis über 27.79 ct/kWh liegen. Das teure Fenster desselben Tages
(38.05 ct/kWh) erfüllt das deutlich.

## Bereitgestellte Entities

| Entity | Bedeutung |
|---|---|
| `sensor.*_empfehlung` | Aktuelle Empfehlung; Attribute tragen Begründung, Quelle, Fenster, Ersparnis, fehlende Daten und die letzten fünf Entscheidungen |
| `sensor.*_ziel_soc` | Ziel-Ladestand in Prozent |
| `sensor.*_empfohlene_ladeleistung` | Rechnerische Ladeleistung für das Fenster |
| `sensor.*_netzleistung` | Summe der konfigurierten Phasen als ein Wert; negativ bedeutet Einspeisung |
| `sensor.*_pv_ueberschuss` | Erkannter Überschuss in Watt |
| `sensor.*_erwarteter_grossverbrauch` | Summe der angekündigten Lasten im Horizont |
| `sensor.*_erwartete_ersparnis` | Geschätzte Ersparnis der Empfehlung |
| `sensor.*_ladefenster_start` / `_ende` | Zeitfenster der Empfehlung |
| `sensor.*_entscheidungsquelle` | Regelbasiert, KI, oder KI ausgefallen |
| `binary_sensor.*_laden_empfohlen` | An, sobald eine der drei Ladeaktionen empfohlen wird |
| `binary_sensor.*_guenstiges_fenster_aktiv` | An, solange ein günstiges Preisfenster läuft |
| `binary_sensor.*_datenbasis_unvollstaendig` | An, wenn Eingangswerte fehlen; Attribut nennt welche |
| `switch.*_ki_entscheidung_nutzen` | Schaltet den KI-Pfad zur Laufzeit ein und aus; Attribute nennen die befragte `ai_task`-Entity und ob der Schalter wirksam ist |

## Steuerung des KI-Pfads

Zwei Stellen mit klarer Aufgabenteilung:

| Ort | Wofür |
|---|---|
| Optionen, Abschnitt „Großverbraucher und KI" | **Welche** `ai_task`-Entity befragt wird, und ob die KI nach einem Neustart aktiviert startet |
| `switch.*_ki_entscheidung_nutzen` | **Ob** sie gerade befragt wird |

Der Schalter schreibt bewusst nicht in die Konfiguration zurück. Täte er das,
würde die Integration bei jedem Umschalten neu geladen und alle Entities
verschwänden kurz. Stattdessen hält er seinen Zustand im Coordinator und
stellt ihn nach einem Neustart über `RestoreEntity` wieder her; nur wenn
keine frühere Aufzeichnung vorliegt, gilt der Wert aus den Optionen.

Ist keine `ai_task`-Entity hinterlegt, bleibt der Schalter bedienbar, hat aber
keine Wirkung – das Attribut `wirksam` macht das sichtbar. Der Schalter ist
der einzige bedienbare Bedienpunkt der Integration und wirkt ausschliesslich
intern; an ein Gerät geht auch von ihm kein Befehl.

## Entscheidungshistorie

Die Empfehlungs-Entity trägt im Attribut `letzte_entscheidungen` die letzten
fünf Entscheidungen, neueste zuerst, jeweils mit Zeitpunkt, Aktion,
Begründung, Erläuterung, Ziel-Ladestand, geschätzter Ersparnis und Quelle.

Ein neuer Eintrag entsteht **nur, wenn sich Aktion oder Begründung
tatsächlich ändern** – sonst läge nach fünf Minuten fünfmal dasselbe in der
Historie. Die Begrenzung auf fünf Einträge ist bewusst: der Wert geht als
Zustandsattribut in die Datenbank.

Das Dashboard zeigt daraus die letzten drei mit vollständiger Erläuterung.
Logbuch und Verlaufsdiagramm können das nicht leisten – sie halten nur den
Zustandswert fest, die Begründung ginge dort verloren.

## Nicht umgesetzt

Die Integration schaltet nichts. Sie besitzt keine `switch`-, `select`- oder
`number`-Plattform und ruft keinen Dienst auf, der ein Gerät verändert – mit
der einen Ausnahme von `ai_task.generate_data`, das ausschliesslich Text
erzeugt. Begründung siehe `strom_v1_open_questions.md`, A2 und C1.
