# Freigabecheckliste v0.2.64-beta.21

## Änderungen / Sicherheit
- [x] Optionaler Headplane-Konfigurationsdialog bei fehlender config.yaml in DE/EN/FR/PT/ES.
- [x] URLs sind Pflichtangaben; keine automatisch erfundene Headscale-Adresse.
- [x] Backend lässt nur den offiziellen Headplane-Dienst mit eigenem absolutem AppData-Config-Mount zu.
- [x] Sichere Dateierstellung im Netzwerk-isolierten, nicht privilegierten Docker-Hilfscontainer, ohne bestehende Dateien zu überschreiben.
- [x] Ausschließlich ein exklusiv angelegtes `config.yaml` unter dem App-Namespace; keine Symlinks.
- [x] Cookie-Secret kryptografisch zufällig; nur über stdin übertragen, nicht in Logs/Antworten.
- [x] Datei wird mit Berechtigungen `0600` erstellt.
- [x] Nach Dateierstellung erfolgt die reguläre Prüfansicht erneut; ohne echte config.yaml bleibt Installation gesperrt.
- [x] Beta 19 und 20 Funktionen unverändert.

## Veröffentlichung
- [ ] GitHub Source Checks des finalen Freigabestands erfolgreich.
- [ ] Docker-Image v0.2.64-beta.21 erfolgreich publiziert, `:beta` bestätigt.
- [ ] Anonymer GHCR-Pull für Versionstag und `:beta` sowie Versionslabel verifiziert.
- [ ] ZimaOS App Store aktualisiert und generierte gh-pages Compose auf Beta 21 überprüft.

## Praxistests (offen)
- [ ] Headplane-Erstinstallation mit tatsächlich laufendem Headscale auf ZimaOS getestet.
- [ ] Cookie-/Config-Dateiberechtigungen und Schreibzugriff auf dem konkreten NAS verifiziert.
- [ ] Erweiterte Headplane-Integrationen nur mit ausdrücklicher Konfiguration aktivieren.

**Keine automatisierte Umgehung von Sicherheits- oder Dateiprüfungen.**
