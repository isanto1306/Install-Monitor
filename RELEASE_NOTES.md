# Install Monitor – Release Notes

## Version 0.2.56 Beta 13 (20.10.2026)

### Neu: Docker-Hub-Projektlinks direkt analysieren
- Unter **GitHub / URL** lassen sich öffentliche Docker-Hub-Image-Seiten eingeben, beispielsweise `https://hub.docker.com/r/clamav/clamav`.
- Unterstützt werden `https://hub.docker.com/r/Herausgeber/Image` und die offiziellen Images unter `https://hub.docker.com/_/Image`; auch der reine `/tags`-Tab wird als Repository-Link erkannt. Filter und Suchparameter werden nicht als Image-Tag fehlinterpretiert.
- Install Monitor ermittelt den exakten Docker-Image-Namen mit dem ausdrücklich ausgewiesenen Standardtag `:latest`, statt HTML von Docker Hub als YAML zu verarbeiten.
- Die bestehende Docker-Image-Analyse wird wiederverwendet: Hersteller-Compose beziehungsweise Docker-Run-Anleitung, sofern verifizierbar vorhanden, ansonsten lokale oder anonyme OCI-Metadaten. Nicht dokumentierte Datenpfade, Ports und Abhängigkeiten werden nicht erfunden.
- Bei Docker-Hub-Link-Importen ist eine erfolgreiche **Registry-Manifestprüfung** des ausgewählten Tags Voraussetzung, bevor eine App an ZimaOS übergeben wird. Die Verfügbarkeit wird nicht allein aus der Docker-Hub-Beschreibung abgeleitet.
- Die Quellenauswahl nennt Docker Hub nun in Deutsch, Englisch, Französisch, Portugiesisch und Spanisch. Der vorhandene Reiter **Docker-Image** bleibt unverändert.

### ClamAV: geschützter Standard
- `clamav/clamav:latest` wird als Virenscanner ohne Weboberfläche behandelt.
- Der ClamAV-Daemon-Port `3310/TCP` wird aus automatisch vorbereiteten Host-Port-Freigaben entfernt, um keinen ungeschützten Scan-Dienst bereitzustellen.
- Scan-Verzeichnisse und Aufträge müssen vom Nutzer ausdrücklich konfiguriert werden. Ein erkannter Image-Tag installiert **keinen** automatischen Virenscan für das gesamte NAS.
- Bei unbekannten Einstellungen erscheint weiterhin die manuell überprüfbare Compose-Vorschau; die Image-Dokumentation ersetzt keine vollständige Betriebsanleitung.

### Validierung und Sicherheit
- Nur HTTPS-Links von `hub.docker.com`, ohne Zugangsdaten, abweichende Ports oder Query-Filter; andere Webseiten werden nicht dadurch freigegeben.
- Der bestehende DNS-/SSRF-Schutz und die ZimaOS-Host-Portprüfung bleiben aktiv.
- Offline-Regressionstests für Namespace-Images, offizielle Library-Images, `/tags`, ungültige bzw. ähnlich aussehende Domains, Weiterleitung zur Herstelleranalyse, OCI-Fallback und ClamAV-Portschutz ergänzt.

### Veröffentlichung
- Backend, Oberfläche, Dokumentation, Installationsskript, lokale Docker-Compose-Vorlage und GHCR-Workflow auf `0.2.56-beta.13` angeglichen.
- Vorgesehene Tags: `ghcr.io/isanto1306/install-monitor:0.2.56-beta.13` und `ghcr.io/isanto1306/install-monitor:beta`.
- Ein erfolgreicher CI-Durchlauf, GHCR-Push, die Store-Veröffentlichung und ein Live-Test auf ZimaOS sind getrennt zu bestätigen.

**Versionsregel:** Nur die Release Notes der aktuellen Beta stehen in dieser Datei. Ältere Versionshinweise werden bei jedem Update ersetzt.
