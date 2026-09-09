# strom_v1 – Installation und Inbetriebnahme

## 1. Voraussetzungen

- Home Assistant 2025.7.0 oder neuer (die Integration nutzt die
  `ai_task`-Plattform; siehe `strom_v1_open_questions.md`, B6)
- Eine Tibber-Preisintegration, deren Zeitraum-Sensoren das Attribut
  `periods` bereitstellen
- Mindestens ein Preissensor und die beiden Zeitraum-Sensoren; alles Übrige
  ist optional

## 2. Installation über HACS

**Voraussetzung: das Repository muss öffentlich sein.** HACS fragt die
GitHub-API ohne Zugriff auf private Repositories ab und bricht sonst mit
`GitHub returned 404 for https://api.github.com/repos/...` ab. GitHub
antwortet bei privaten Repositories bewusst mit 404 statt 403, damit deren
Existenz nicht verraten wird – die Meldung bedeutet also nicht, dass das
Repository fehlt.

Sichtbarkeit anonym prüfen:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.github.com/repos/aschmidtlev/strom-optimierung
```

`200` heisst öffentlich, `404` privat. Ein erfolgreiches `git push` oder
`git ls-remote` ist **kein** Nachweis – dort liefert der Credential-Manager
die gespeicherten Zugangsdaten.

Umstellen unter **GitHub → Repository → Settings → General → Danger Zone →
Change repository visibility → Make public**.

Danach:

1. In HACS **Benutzerdefinierte Repositories** öffnen.
2. `https://github.com/aschmidtlev/strom-optimierung` als Typ *Integration*
   hinzufügen.
3. „Strom-Optimierung" installieren.
4. Home Assistant neu starten.

Soll das Repository privat bleiben, ist die manuelle Installation nach
Abschnitt 3 der Weg – sie kommt ohne HACS aus.

### 2.1 Neue Versionen sichtbar machen

HACS ermittelt die Version eines Custom Repositories über die
**GitHub-Releases**, nicht über `manifest.json` und nicht über Git-Tags. Eine
angehobene Versionsnummer im Manifest allein führt deshalb zu keinem
Update-Hinweis, und ein `git tag` allein ebenfalls nicht: GitHub erzeugt aus
einem Tag kein Release.

Gegenprüfen lässt sich das so:

```bash
curl -s https://api.github.com/repos/aschmidtlev/strom-optimierung/releases
```

Kommt `[]` zurück, existiert kein Release – dann verfolgt HACS den
Standardbranch und zeigt keine Versionssprünge an.

**Das Release entsteht automatisch.** `.github/workflows/release.yml` legt zu
jedem gepushten Tag ein GitHub-Release an. Die Action nutzt nur das
eingebaute Token des Runners und die dort vorinstallierte GitHub-CLI – kein
eigenes Geheimnis, keine fremde Action. Existiert zum Tag bereits ein
Release, tut sie nichts, ein erneuter Tag-Push ist also unschädlich.

Für eine neue Version genügen damit zwei Schritte:

1. Version in `custom_components/strom_optimierung/manifest.json` anheben und
   auf `main` pushen.
2. Tag mit derselben Nummer setzen und pushen:
   `git tag -a 0.1.2 -m "Version 0.1.2" && git push origin 0.1.2`

Rund eine halbe Minute später steht das Release. Danach in HACS beim
Repository über das Dreipunktmenü **Informationen aktualisieren** wählen –
anschliessend wird die neue Version zum Herunterladen angeboten. Nach dem
Download Home Assistant neu starten.

Wird ein Tag versehentlich auf den falschen Commit gesetzt, lässt er sich
verschieben, solange noch kein Release daran hängt:

```bash
git push origin :refs/tags/0.1.2
git tag -f -a 0.1.2 -m "Version 0.1.2" HEAD
git push origin 0.1.2
```

## 3. Manuelle Installation

Den Ordner `custom_components/strom_optimierung` in das
`custom_components`-Verzeichnis der Home-Assistant-Konfiguration kopieren und
Home Assistant neu starten.

## 4. Einrichtung

Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach
„Strom-Optimierung" suchen. Der Dialog führt durch vier Schritte. Alle
Felder sind mit den Entities der Zielanlage vorbelegt; die Vorschläge lassen
sich überschreiben.

**Schritt 1 – Strompreis.** Aktueller Preis sowie die beiden Zeitraum-Sensoren
sind Pflicht. Wichtig: Es müssen die *Zeitraum*-Sensoren gewählt werden
(`binary_sensor.home_bestpreis_zeitraum` und
`binary_sensor.home_spitzenpreis_zeitraum`), nicht die Start-/Ende-Sensoren –
nur sie tragen das Attribut `periods`.

**Schritt 2 – PV und Netz.** Bei den beiden Prognosefeldern jeweils die
Sensoren **beider** PV-Anlagen auswählen; sie werden summiert. Beim Feld
Netzleistung alle drei Phasen des Shelly Pro 3EM auswählen.

**Schritt 3 – Speicher und Grenzwerte.** Der Ladestand ist bewusst **nicht**
vorbelegt, weil `sensor.marstek_venus_modbus_soc_batterie` im Snapshot
`unavailable` war. Sobald die Modbus-Verbindung wieder steht, kann er hier
nachgetragen werden. Ohne Ladestand arbeitet die Logik eingeschränkt weiter
und meldet das über `binary_sensor.*_datenbasis_unvollstaendig`.

**Schritt 4 – Großverbraucher und KI.** Der KI-Pfad ist standardmässig aus.
Wird er eingeschaltet, muss eine `ai_task`-Entity gewählt werden.

**Alle vier Bereiche** lassen sich später über **Konfigurieren** an der
Integration erneut öffnen. Der Dialog zeigt dafür ein Menü mit denselben vier
Abschnitten; es lassen sich also auch Quell-Entities und der KI-Pfad
nachträglich ändern, nicht nur die Grenzwerte.

Den KI-Pfad im laufenden Betrieb ein- und auszuschalten geht schneller über
`switch.strom_optimierung_ki_entscheidung_nutzen`. Der Schalter lädt die
Integration nicht neu; die Option im Dialog legt nur fest, mit welchem
Zustand sie nach einem Neustart startet, falls kein früherer Zustand
vorliegt.

## 5. Prüfung nach der Einrichtung

1. Unter **Entwicklerwerkzeuge → Zustände** prüfen, dass
   `sensor.strom_optimierung_empfehlung` einen der Werte `idle`, `charge_pv`,
   `charge_price`, `charge_anticipatory` oder `hold` zeigt – nicht
   `unavailable`.
2. Das Attribut `erlaeuterung` desselben Sensors lesen: es beschreibt in
   Klartext, warum genau diese Empfehlung gilt.
3. `binary_sensor.strom_optimierung_datenbasis_unvollstandig` prüfen. Steht
   er auf *an*, nennt sein Attribut `fehlende_daten`, welche Eingangswerte
   fehlen. Solange der Marstek ausgefallen ist, wird dort „Speicher-SoC"
   stehen – das ist erwartet.
4. Das Home-Assistant-Protokoll auf Einträge des Loggers
   `custom_components.strom_optimierung` prüfen.

## 6. Dashboard einspielen

1. **Einstellungen → Dashboards → Dashboard hinzufügen**, leeres Dashboard
   anlegen.
2. Im neuen Dashboard oben rechts **Bearbeiten**, dann im Dreipunktmenü
   **Rohkonfigurationseditor**.
3. Den vollständigen Inhalt von `strom_v1_dashboard.yaml` einfügen und
   speichern.

Für das Flussdiagramm wird `power-flow-card-plus` benötigt (über HACS unter
Frontend). Auf der Zielanlage ist die Karte bereits installiert. Fehlt sie,
meldet nur diese eine Karte einen Fehler – alle übrigen Karten und Ansichten
funktionieren, und die native Karte „Leistungsbilanz" direkt darunter zeigt
dieselben Werte.

Der Batteriespeicher fehlt bewusst im Flussdiagramm, solange der Marstek
keine Daten liefert. Zum Nachrüsten steht der fertige Konfigurationsblock
als Kommentar in der Datei; die drei nötigen Schritte sind dort beschrieben.

Die Karte **Letzte drei Entscheidungen** in der Ansicht *Entscheidung* zeigt
direkt nach der Installation den Hinweis „Noch keine Entscheidung
aufgezeichnet" – das ist erwartet. Der erste Eintrag entsteht mit dem ersten
Durchlauf, ein zweiter erst, wenn sich Aktion oder Begründung ändern.

## 7. Testbetrieb

Die Integration schaltet nichts. Sie kann deshalb gefahrlos mitlaufen. Für
die ersten Tage empfiehlt sich, den Verlauf von
`sensor.strom_optimierung_empfehlung` zu beobachten und mit dem tatsächlichen
Preisverlauf abzugleichen:

- Empfiehlt sie `charge_price` in den erkennbar günstigen Stunden?
- Springt sie bei Sonne auf `charge_pv`? Falls nie, ist vermutlich die
  Vorzeichenannahme des Netzzählers falsch – siehe
  `strom_v1_open_questions.md`, B1.
- Kündigt sie vor der Warmwasserladung `charge_anticipatory` an?

Erst wenn diese Beobachtung überzeugt, lohnt es sich, über eine Aktorebene zu
sprechen.

## 8. Tests ausführen

In einer Umgebung mit Python 3.12 oder neuer:

```bash
pip install -r requirements-test.txt
pytest
```

Die Tests wurden auf dem Entwicklungsrechner **nicht ausgeführt**, weil dort
kein nutzbarer Python-Interpreter installiert ist – siehe
`strom_v1_open_questions.md`, B5.

## 9. Rollback

Die Integration über **Einstellungen → Geräte & Dienste** löschen, den Ordner
`custom_components/strom_optimierung` entfernen und das Dashboard unter
**Einstellungen → Dashboards** löschen. Es bleiben keine
Rückstände an anderen Systemen zurück, da nichts geschaltet und nichts an
fremden Entities verändert wird. `ww_v3` ist zu keinem Zeitpunkt betroffen.
