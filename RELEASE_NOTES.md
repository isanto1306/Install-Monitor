# Install Monitor – Release Notes

## Version 0.2.58 Beta 15 (20.10.2026)

### ZimaOS-Hersteller-Compose bevorzugen
- Bei GitHub-Projekten werden geprüfte herstellereigene ZimaOS/CasaOS-Bundles in eindeutigen App-Ordnern bevorzugt. Ein bloßer Dateiname ist kein Herkunftsnachweis: Der Inhalt muss zum Projekt passen.
- Für Nametag wird damit die offizielle ZimaOS-Bereitstellung in `deploy/zimaos/Nametag/docker-compose.yml` gegenüber der allgemeinen Produktions-Compose bevorzugt. Direkte Compose-Datei-URLs bleiben unverändert.
- Ausschließlich wörtliche, vom ZimaOS-Hersteller-Template bekannte `/DATA/AppData/$AppID/...`-Bind-Mounts werden auf den ausgewählten app-spezifischen NAS-Pfad abgebildet. Andere Volumes und Shellvariablen bleiben unverändert.

### Externe Netzwerke vor ZimaOS-POST kontrollieren
- Für `external: true` wird das vorhandene Docker-Netzwerk auf dem tatsächlichen NAS geprüft. Fehlt ein benötigtes Netzwerk oder ist die Prüfung nicht möglich, wird der Installationsauftrag mit einer konkreten Meldung gesperrt.
- Externe Proxy-Netze werden aus Sicherheitsgründen nicht eigenmächtig erstellt, gelöscht oder durch scheinbar gleichnamige leere Netze ersetzt.

### Initialisierungscontainer und Diagnose
- Mit `depends_on: condition: service_completed_successfully` referenzierte Einmal-Initialisierungen (`restart: "no"`) gelten nach Exit 0 als erfolgreich. Ihre Container müssen nicht dauerhaft laufen.
- Ohne erstellte Container wird nach Zeitlimit ausdrücklich „keine Container erstellt“ statt eines pauschalen Healthcheck-Fehlers gemeldet; fehlende Images werden namentlich aufgeführt, sofern lokal prüfbar.
- Bestehende Port-, Credential-, Host-Rechte- und Compose-Prüfungen bleiben bestehen.

### Veröffentlichung
- Backend, statische Oberfläche, Installer, lokale Compose-Vorlage und GHCR auf `0.2.58-beta.15` aktualisiert.
- Vorgesehene Images: `ghcr.io/isanto1306/install-monitor:0.2.58-beta.15` und `:beta`.
- Der iSanto1306 ZimaOS App Store wird erst nach erfolgreicher GHCR-Veröffentlichung synchronisiert.
- Ein erfolgreicher CI-Lauf ersetzt keinen praktischen Nametag-/ZimaOS-Test auf dem NAS.

**Versionsregel:** Nur Hinweise zur aktuellen Beta stehen hier.
