# Freigabecheckliste v0.2.62-beta.19

## Quellcode / automatisierte Tests
- [x] Originalfunktionen Beta 15–18 bleiben erhalten; neue Umwandlung isoliert auf ZimaOS.
- [x] AppData-Mounts für gewöhnliche benannte Docker-Volumes teilen dieselben Daten über alle Dienste.
- [x] Vorhandene Docker-Volumes, externe oder speziell konfigurierte Volumes und unklare Mountoptionen bleiben unverändert.
- [x] :ro/Schreibschutz, Mountziele und bestehende Host-Binds werden erhalten.
- [x] Automatische Tests für RSSMonster mit drei Diensten, Sonderfälle und Installationsvorschau vorhanden.
- [x] GitHub-CI für Beta-19-Freigabecommit erfolgreich (GitHub Actions).
- [x] GHCR-Image v0.2.62-beta.19 gebaut; anonymer Pull von Version und :beta erfolgreich geprüft.
- [x] Zima-App-Store nach erfolgreicher Veröffentlichung aktualisiert und gh-pages Compose-Version kontrolliert.

## Sicherheit / NAS-Praxistests
- [ ] Erstinstallation auf separatem frischen ZimaOS-NAS einschließlich Verzeichnisrechten und leerer Bind-Mounts praktisch verifizieren.
- [ ] Testanwendung mit Image-Initialdateien auf fehlendes Docker-Volume-Copy-up prüfen.
- [ ] Vorherigen privaten GitHub-PAT gegebenenfalls widerrufen/rotieren; Authenticator-/Session-Secrets überprüfen.
- [ ] Git-Historie separat auf möglicherweise frühere Secrets prüfen (Quellcode-Prepublish-Scan ersetzt keine Historienprüfung).
- [ ] Native Dashboard-/Store-Integration auf einer echten ZimaOS-Instanz bestätigen.

## Veröffentlichung
- [x] Lizenz GPL-3.0-only und Third-Party-Hinweise beibehalten.
- [x] Keine Benutzer-Geheimnisse oder NAS-Zugangsdaten in Commit oder Tests.
- [ ] Finalen Release-TAG (optional) erst nach gesonderter Freigabe anlegen.

**Beta-Status:** Automatische CI und GHCR-Veröffentlichung belegen keine universelle Kompatibilität von Drittanbieter-Containern. Bestehende Installationen nicht mit dem Erstinstallationsskript überschreiben.
