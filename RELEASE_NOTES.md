# Install Monitor – Release Notes

## Version 0.2.63 Beta 20 (24.10.2026)

### Headplane: offizielle Docker-Installation statt Entwickler-Compose
- Die GitHub-Repository-Quelle `https://github.com/tale/headplane` verwendet die offizielle Docker-Installationsanleitung `https://headplane.net/install/docker`, nicht länger die Root-`compose.yaml` aus der Entwicklerumgebung.
- Headplane wird als eigener Hauptdienst mit `ghcr.io/tale/headplane:latest` und internem Port 3000 angeboten. Kein automatisch hinzugefügter Test-Headscale, Caddy, Entwicklungsnetzwerk oder Testzertifikat.
- Notwendige Host-Konfiguration und persistente App-Daten werden im gewählten ZimaOS-AppData-Bereich gemountet. Die Datei `config.yaml` bleibt **Pflicht** und muss als reguläre Datei auf dem NAS existieren.
- Wird die eindeutig erkennbare Headplane-Entwickler-`compose.yaml` direkt als YAML oder Datei-URL importiert, erscheint eine Erklärung statt eines fälschlich installierbaren Stacks.

### Relative Konfigurationsdateien in Compose
- Sichere, relative Datei-Mounts wie `./config.yaml:/etc/headplane/config.yaml` erhalten bei ZimaOS den absoluten AppData-Quellpfad `/DATA/AppData/headplane/config.yaml:/etc/headplane/config.yaml`.
- Identische relative Dateiquellen werden in allen betroffenen Diensten konsistent auf denselben Hostpfad gemappt. Zielpfad und Schreibschutz bleiben erhalten.
- Die Umwandlung **erstellt keine Dateien**, importiert keine unbelegten GitHub-Nebendateien und umgeht weder die Hostdatei-/Symlink-Prüfung noch andere Installationssperren.
- Relative Traversal-Pfade wie `../secret.yaml` sowie explizite `bind.create_host_path: true`-Mounts werden nicht automatisch umgeschrieben.
- Die Änderung greift nur bei ZimaOS-Zielen. Andere Compose-Zielsysteme behalten ihre bisherigen Regeln.

### Voraussetzungen und Grenzen
- Headplane braucht einen bereits eingerichteten Headscale-Server und eine gültige `config.yaml` mit `headscale.url` und `server.cookie_secret` (32 zufällige Zeichen).
- Die Sicherheitsprüfung einer fehlenden oder nicht regulären Konfigurationsdatei bleibt aktiv: Ohne echte Hostdatei keine Installation.
- Ein erfolgreicher GitHub-Test beweist nicht, dass das Drittanbieter-Image auf jedem ZimaOS-NAS bereits funktionsfähig ist.
- Die Umwandlung früherer Beta 19 von gewöhnlichen benannten Volumes nach AppData bleibt unverändert, ohne bestehende Docker-Daten automatisch zu migrieren.

### Veröffentlichung
- Version: `0.2.63-beta.20`
- Docker-Image: `ghcr.io/isanto1306/install-monitor:0.2.63-beta.20`
- `:beta` verweist nach erfolgreichem Build auf diese Version.
- ZimaOS App Store wird nur mit bestätigtem öffentlichen GHCR-Image aktualisiert.

**Versionsregel:** Nur die aktuelle Beta wird hier dokumentiert.
