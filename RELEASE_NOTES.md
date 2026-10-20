# Install Monitor – Release Notes

## Version 0.2.61 Beta 18 (20.10.2026)

### Docker Compose aus unvollständigen Hersteller-Beispielen ergänzen
- Der Compose-YAML-Import erkennt eindeutig definierte einzelne oder mehrere Docker-Dienste, wenn nur die übergeordnete `services:`-Zeile fehlt. Bei echten Dienstzuordnungen mit `image` oder `build` wird der fehlende Compose-Strukturblock sicher ergänzt.
- Vorhandene `networks`-, `volumes`-, `name`- und `x-*`-Metadaten bleiben erhalten; Service-Definitionen, Secrets, Volumes und Ports werden nicht erfunden.
- Mehrdeutige, fehlerhafte oder ausdrücklich unvollständige Compose-Dateien bleiben unverändert und werden wie bisher mit einer konkreten Meldung abgewiesen.
- Die automatische Reparatur erfolgt vor der ersten Quellanalyse; Beta 17 kann anschließend Konfigurations-Beispielpfade zuordnen und eindeutige gemeinsame NAS-Medienpfade auflösen.
- Regressionstests prüfen direkte Hersteller-Service-Snippets, mehrere Dienste, vorhandene Top-Level-Volumes und Netzwerke, unveränderte Rechte und Mounts, vorsichtige Ablehnung von Fehlkonfigurationen sowie die komplette Quellanalyse bis zur Installationsvorschau.

### Bestehende Funktionen bleiben erhalten
- Beta 17: Sichere automatische NAS-AppData-Ordnerzuordnung, eindeutige Medienmount-Erkennung und eine einzige Rückfrage bei Mehrdeutigkeit.
- Beta 16: Shell-Befehle und Cron-Variablen bleiben bei wiederholter ZimaOS-Compose-Auswertung erhalten.
- Beta 15: Hersteller-ZimaOS-Compose bevorzugen, fehlende externe Netzwerke frühzeitig erkennen, einmalige Initialisierungscontainer korrekt behandeln.

### Veröffentlichung
- Backend, Docker-Compose, Installer, Oberfläche und GHCR-Workflow verwenden `0.2.61-beta.18`.
- Image-Tags: `ghcr.io/isanto1306/install-monitor:0.2.61-beta.18` und `:beta`.
- iSanto1306 Zima-App-Store nach erfolgreichem GHCR-Build synchronisieren.
- GitHub-Tests ersetzen keinen NAS-Praxistest.

**Versionsregel:** Nur die aktuelle Beta wird hier dokumentiert.
