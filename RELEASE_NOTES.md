# Install Monitor – Release Notes

## Version 0.2.56 Beta 5 (19.10.2026)

### Behoben
- NetAlertX: Die Host-Netzwerk-Portprüfung erkennt den offiziellen Web-Port über `PORT` und den GraphQL-Port über `GRAPHQL_PORT`.
- Compose-Standardwerte wie `${PORT:-20211}` und `${GRAPHQL_PORT:-20212}` werden für NetAlertX ausgewertet.
- Beide TCP-Ports werden vor Installation auf Konflikte geprüft. Fehlende oder identische Portangaben werden ausdrücklich gemeldet.
- `network_mode: host` bleibt unverändert; Docker-Portweiterleitungen werden nicht erfunden.

### Veröffentlichung
- Versionsangaben in Backend, Oberfläche, Installationsskript, Docker Compose und Dokumentation auf Beta 4 angeglichen.
- GHCR-Publishing auf `ghcr.io/isanto1306/install-monitor:beta` und `ghcr.io/isanto1306/install-monitor:0.2.56-beta.5` umgestellt.

### Hinweise
- Bei Host-Networking können weitere, nicht dokumentierte Netzwerkports verwendet werden. Diese Prüfung deckt ausdrücklich die beiden genannten NetAlertX-Ports ab, nicht sämtliche Netzwerkaktivität.
- Veröffentlichung des Images und Laufzeittest auf ZimaOS sind separat zu prüfen.

Diese Datei enthält absichtlich **nur die Release Notes der aktuellen Version**. Beim nächsten Update wird sie ersetzt, nicht angehängt.
