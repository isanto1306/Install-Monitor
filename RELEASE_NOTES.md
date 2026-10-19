# Install Monitor – Release Notes

## Version 0.2.56 Beta 7 (19.10.2026)

### Neu: Codeberg-/Forgejo-Repository-Erkennung
- Öffentliche Projektlinks wie `https://codeberg.org/irelephant/kittygram` können jetzt auf Docker-Compose-Dateien untersucht werden. Ein direkter YAML-Link ist nicht mehr zwingend erforderlich.
- Der Install Monitor nutzt nach Möglichkeit die öffentliche Codeberg-API zur Bestimmung des Standardbranches und zur Suche geeigneter Dateien, mit begrenztem Fallback auf übliche Compose-Dateinamen und Installationsordner.
- Unterstützt werden auch Codeberg-Dateiseiten der Form `/src/branch/.../compose.yaml` und direkte `/raw/branch/...`-Links.
- Erkannte YAML-Dateien werden vor der Übernahme als Docker Compose validiert. Fremde YAML-Dateien ohne gültige `services`-Konfiguration werden nicht als Compose akzeptiert.
- Der Projektlink bleibt in der Analyse erhalten. Auch für Codeberg-Projekte wird ein sinnvoller App-Name aus dem Projektpfad übernommen.

### Einschränkungen und Sicherheit
- Compose-Dateien mit `build:` können erkannt werden. Die automatische Übergabe eines vollständigen **Codeberg-Build-Kontexts** einschließlich möglicher Git-LFS-Dateien ist noch nicht implementiert. Die Analyse meldet die Voraussetzung; eine Installation ohne nachgewiesenen vollständigen Build oder veröffentlichtes Image wird gesperrt.
- Codeberg-Adressen müssen HTTPS verwenden. Abrufe sind auf bekannte Codeberg-Hosts begrenzt; Dateisuche und Downloads sind begrenzt. Es werden keine Skripte aus entfernten Projekten ausgeführt.
- Für Kittygram (`irelephant/kittygram`) enthält das Originalprojekt eine `compose.yaml` mit lokalem Build. Die Dateierkennung allein bestätigt deshalb keinen funktionierenden ZimaOS-Start.

### Tests
- Regressionstests für Codeberg-Projektlinks, Dateiseiten, fehlende Compose-Dateien und ungültige Dateipfade hinzugefügt.
- Erfolgreicher Docker-Build, Image-Push und Live-Test auf ZimaOS müssen separat bestätigt werden.

### Veröffentlichung
- Backend, Oberfläche, Dokumentation, lokale Compose-Vorlage, Installationsskript und GHCR-Workflow auf `0.2.56-beta.7` angeglichen.
- Vorgesehene Tags: `ghcr.io/isanto1306/install-monitor:beta` und `ghcr.io/isanto1306/install-monitor:0.2.56-beta.7`.

**Versionsregel:** Diese Datei enthält ausschließlich die Release Notes der aktuellen Version. Bei der nächsten Beta werden sie ersetzt, nicht angehängt.
