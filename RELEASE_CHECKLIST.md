# Freigabecheckliste v0.2.63-beta.20

## Funktionsumfang
- [x] Headplane-Repository verweist auf die offizielle Docker-Installationsvariante statt auf die Entwickler-Compose.
- [x] Direkter Import der eindeutig erkennbaren Headplane-Entwickler-Compose wird mit Erklärung blockiert.
- [x] Sichere relative Konfigurationsdatei-Mounts werden für ZimaOS auf absolute AppData-Pfade abgebildet.
- [x] Datei-Ziel, Schreibschutz und gemeinsame Dateiquelle über mehrere Services bleiben erhalten.
- [x] Keine automatische Erstellung, Übernahme oder Überschreibung der Datei config.yaml.
- [x] Ursprüngliche Dateitypprüfung und Installationssperren bleiben aktiv.
- [x] Unsichere relative Traversal-Pfade werden nicht automatisch umgesetzt.
- [x] Beta 19 AppData-Volume-Konvertierung wird nicht verändert.

## Veröffentlichung / CI
- [ ] Source Checks am finalen Freigabecommit erfolgreich.
- [ ] GHCR Version 0.2.63-beta.20 gebaut, und öffentlicher Pull mit Versionstag und :beta bestätigt.
- [ ] ZimaOS App Store mit bestätigtem GHCR-Image aktualisiert und erzeugte gh-pages Compose kontrolliert.

## Praxis / Sicherheit
- [ ] Erstinstallation von Headplane mit gültiger config.yaml und laufendem Headscale auf einem echten ZimaOS-NAS verifiziert.
- [ ] Konfigurationsdatei vor der Installation auf Host-Dateityp und passende Zugriffsrechte prüfen.
- [ ] Weitere reale Compose-Projekte auf relative Datei-Mounts prüfen.
- [ ] Vorherige noch offene Security-Checkpunkte (z. B. Tokenrotation) separat abschließen.

Diese Sicherheitschecks werden nicht übersprungen, um die Installation zu erzwingen.
