# Install Monitor – Release Notes

## Version 0.2.60 Beta 17 (20.10.2026)

### Automatische Hersteller-Pfadzuordnung beim Compose-Import
- Ordnerplatzhalter wie `/path/to/sonarr/config` oder `/path/to/mkvpriority/config` werden im regulären Installationsassistenten selbstständig in app-eigene Ordner unter `/DATA/AppData/<App-Name>/...` überführt. Die Ordner werden wie bisher erst unmittelbar vor der Installation sicher vorbereitet.
- Gemeinsame Hersteller-Medienplatzhalter (`/path/to/media`) werden aus eindeutig vorhandenen, schreibgeschützt geprüften NAS-Ordnern und Docker-Bind-Mounts übernommen. Eine bereits ausdrücklich für einen Dienst ausgewählte Medienquelle hat Vorrang und wird für andere Dienste desselben Stacks wiederverwendet.
- Existieren keine oder mehrere verschiedene mögliche Quellen, bleibt der Platzhalter erhalten und Install Monitor fordert genau eine Medienordner-Auswahl an; keine erfundenen Medienbibliotheken, keine neuen Medienordner.
- Mehrfach gemeldete Beispielpfade werden zu einer einzigen verständlichen Meldung pro gemeinsamer Quelle zusammengefasst.
- Existierende Mounts, benannte Docker-Volumes, Dateimounts, read-only-Angaben und Mount-Zielpfade bleiben unverändert. Bestehende Sonarr-Konfigurationen anderer Installationen werden nicht stillschweigend geteilt oder verändert.
- Die Erkennung liest nur begrenzte Docker-Mount-Metadaten und wenige existierende NAS-Ordner; keine Container-Neustarts, kein Lesen von Geheimnissen.

### Fortgeführte Funktionen
- Beta 16: Shell-Variablen in Hersteller-Initialisierung und Cron-Skripten werden sicher durch die ZimaOS-Compose-Verarbeitung transportiert.
- Beta 15: Offizielle ZimaOS-Konfigurationen bevorzugen, externe Netzwerke vorab prüfen und Einmal-Initialisierungscontainer korrekt erkennen.
- Beta 14: Unterstützte lokale Secrets und Compose-Werte konservativ automatisch auflösen; tatsächliche NAS-Zeitzone nutzen.

### Veröffentlichung
- Backend, Docker-Compose, Installer, Web-Oberfläche und GHCR-Workflow verwenden `0.2.60-beta.17`.
- Vorgesehene Image-Tags: `ghcr.io/isanto1306/install-monitor:0.2.60-beta.17` und `:beta`.
- Der iSanto1306 Zima-App-Store wird nach erfolgreichem GHCR-Build aktualisiert.
- Ein erfolgreicher Offline-CI-Test ersetzt keinen Praxistest mit ZimaOS.

**Versionsregel:** Diese Datei dokumentiert nur die aktuelle Beta.
