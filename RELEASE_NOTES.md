# Install Monitor – Release Notes

## Version 0.2.56 Beta 8 (19.10.2026)

### Neu: Codeberg-Quellcode direkt für ZimaOS bauen
- Codeberg-Projekte mit einer Docker-Compose-Datei und `build:` können jetzt einen lokalen NAS-Build vorbereiten.
- Install Monitor ermittelt den Original-Commit über die Codeberg-API. Die Compose-Datei wird am unveränderlichen Commit erneut gelesen und mit der zuvor analysierten Datei abgeglichen.
- Ein Original-Image wie `kittygram:latest`, das nur für lokale Builds vorgesehen ist, wird im Entwurf durch ein eindeutiges Image `installmonitor-local/…:<commit>` ersetzt.
- Der bestätigte Commit wird per HTTPS mit Git abgerufen. Falls sich der Branch zwischen Analyse und Download verändert, stoppt die Installation.
- Git LFS wird berücksichtigt: Benötigte Dateien werden vor dem Docker-Build heruntergeladen und auf vollständig ersetzte LFS-Pointer geprüft.
- Der Build verwendet den vorhandenen Install-Monitor-Ablauf: lokales Docker-Image bauen, in die ausschließlich auf `127.0.0.1:50813` gebundene Registry übertragen und über die ZimaOS-App-API installieren. Die normale ZimaOS-Kachel bleibt Ziel des Ablaufs.

### Sicherheit und Grenzen
- Fremder Dockerfile-Quellcode wird erst nach ausdrücklicher Build-Bestätigung ausgeführt. Quellcode selbst wird nicht ausgeführt, bevor die Bestätigung vorliegt.
- Externe Submodule werden nicht automatisch initialisiert.
- Für Git LFS gelten Größenlimits (insgesamt maximal 256 MiB LFS-Daten); die ausgecheckte Quelle wird ebenfalls begrenzt.
- Öffentliche Codeberg-Repositories, einfache Branch-Namen und vollständige, unterstützte Docker-Konfigurationen sind erforderlich. Projekte mit zusätzlichen, nicht übertragenen Dateien, Anmeldeinformationen oder nicht unterstützten Build-Optionen bleiben blockiert.
- Die Änderung bedeutet **keine Garantie**, dass Kittygram auf jedem ZimaOS-NAS startet. Ressourcen, Ports und konkrete Laufzeitabhängigkeiten müssen nach dem Build geprüft werden.

### Qualitätsprüfung
- Offline-Regressionstests für unveränderliche Commit-Bindung, Vergleich der geprüften Compose, Image-Namen, Git LFS, Größenlimits und Abbruch bei verändertem Branch hinzugefügt.
- Dockerfile um `git` und `git-lfs` erweitert.
- Oberfläche und Build-Bestätigung für GitHub-/Codeberg-Quellen angepasst.

### Veröffentlichung
- Backend, Frontend, Dokumentation, Docker-Compose-Vorlage, Installationsskript und GitHub-Actions-Workflow auf `0.2.56-beta.8` aktualisiert.
- Vorgesehene GHCR-Tags: `ghcr.io/isanto1306/install-monitor:beta` und `ghcr.io/isanto1306/install-monitor:0.2.56-beta.8`.

**Versionsregel:** Diese Datei enthält ausschließlich die Release Notes der aktuellen Version. Bei der nächsten Version werden frühere Hinweise vollständig ersetzt.

**Verifizierungsstatus:** Ein erfolgreicher GHCR-Build und ein echter Kittygram-Installationstest auf ZimaOS müssen gesondert bestätigt werden.
