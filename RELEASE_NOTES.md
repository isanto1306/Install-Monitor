# Install Monitor – Release Notes

## Version 0.2.56 Beta 9 (19.10.2026)

### Behoben: Codeberg-Projekte mit Docker-Anleitung in der README
- Bei Codeberg-Projekten ohne eigenständige `compose.yml`, `compose.yaml` oder `docker-compose.yml` wird jetzt auch die Original-README beziehungsweise die veröffentlichte Docker-Installationsdokumentation auf vollständige Compose-Beispiele geprüft.
- Markdown-Codeblöcke (`yaml`, `yml`, `compose`, `docker-compose`) werden nur als Docker Compose übernommen, wenn sie einen vollständigen, gültigen `services`-Block mit konkreten Docker-Images enthalten.
- Die Compose-Konfiguration muss mindestens ein Image enthalten, dessen Registry-Pfad exakt zum Eigentümer und Namen des Codeberg-Projekts passt. Unzugehörige Beispiel-Stacks werden nicht übernommen.
- Die Quelle wird als **README-Beispiel** ausgewiesen, nicht fälschlich als eigenständige Compose-Datei. Container-Images aus solchen Anleitungen erhalten eine verpflichtende Registry-Manifestprüfung vor jedem Installationsauftrag.
- Der direkte Compose-Dateifund bleibt bevorzugt. README-Beispiele sind ausschließlich ein Fallback.

### Beispiel: DanB/RSS
- `https://codeberg.org/danb/rss` enthält eine dokumentierte Docker-Compose-Konfiguration, obwohl keine eigenständige Compose-Datei gefunden wird.
- Verwendetes offizielles Image: `codeberg.org/danb/rss:latest`. Docker-Build ist hierfür **nicht** erforderlich.
- Die README-Installation nutzt Container-Port `80` und ein persistentes Verzeichnis unter `/app/storage`. Im Install Monitor sind Host-Port und AppData-Ordner vor der Installation auswählbar.
- Sicherheit: DanB/RSS bietet laut Dokumentation keinen eingebauten Anmeldeschutz. Keine ungeschützte Veröffentlichung ins Internet; Zugriff durch Netzwerksegmentierung oder vorgeschaltete Authentifizierung absichern.

### Sicherheit und Tests
- Unvollständige YAML-Fragmente, nicht zugehörige Images und lokale Build-Beispiele ohne fertiges Image werden nicht automatisch als installierbar eingestuft.
- Offline-Regressionstests für README-Fallback, Publisher-Image-Abgleich, unvollständige Compose-Beispiele und Vorrang einer echten Compose-Datei ergänzt.
- Unveränderte Funktionen: Github-/Codeberg-Builds, ZimaOS-App-Registrierung und bestehende Docker-Image-Installationen.

### Veröffentlichung
- Backend, Oberfläche, Docker-Compose-Vorlage, Installationsskript, Dokumentation und GHCR-Publish-Workflow auf `0.2.56-beta.9` aktualisiert.
- Ziel-Tags: `ghcr.io/isanto1306/install-monitor:beta` und `ghcr.io/isanto1306/install-monitor:0.2.56-beta.9`.
- Erfolgreicher CI-Testlauf, GHCR-Push und tatsächliche ZimaOS-Installation sind erst nach separater Überprüfung bestätigt.

**Versionsregel:** Diese Datei enthält ausschließlich die aktuellen Release Notes. Beim nächsten Update werden ältere Einträge ersetzt und nicht angehängt.
