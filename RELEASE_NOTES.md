# Install Monitor – Release Notes

## Version 0.2.65 Beta 22 (29.10.2026)

### Systematische Prüfung von vier Importwegen
- Vier vergleichbare Eingänge in Regressionstests: **Docker-Image, GitHub/URL, direktes Compose-YAML und LinuxServer.io App-Katalog**.
- Weitere iSanto1306-Katalog-Apps verwenden den URL-Import für ihre Compose-Datei; sie benötigen keine separate, konkurrierende Umwandlungslogik.
- Eine dokumentierte Prüfmatrix erklärt je Quelle Portzuordnung, AppData, Unbekanntes und Herstellerabhängigkeiten: `AUDIT_IMPORT_PATHS.md`.

### Automatische Portzuordnung verbessert
- Fehlt eine `ports:`-Abbildung, kann Install Monitor einen Host-Port ergänzen, **wenn genau ein interner HTTP-Web-Port durch einen containerlokalen Healthcheck eindeutig nachgewiesen wird**.
- Bereits vorhandene `expose:`-Angaben dürfen dem ermittelten TCP-Port nicht widersprechen. Vorhandene explizite `ports:`-Angaben werden nicht überschrieben.
- Bei URL-/GitHub-Importen wird jetzt – wie zuvor für Image-Importe – eine bereits belegte Host-Portbelegung auf eine tatsächlich vom NAS geprüfte freie Alternative umgestellt. Bewusst eingegebenes YAML mit vorhandenen Portzuordnungen bleibt unverändert.
- Datenbanken, Worker, Host-Netzwerk, optionale nicht aktive Profile und bewusst nur via Reverse Proxy erreichbare Anwendungen erhalten keine zusätzliche Portveröffentlichung.
- Bei fehlendem Beleg für einen HTTP-Port erfindet Install Monitor keine Portnummer und verlangt weitere Herstellerangaben.

### Regressionstests und Datenverzeichnisse
- Neue Tests prüfen über die vier Quelltypen hinweg identische deklarierte Webports und Bildzuordnungen, fehlende Webports mit Healthcheck, nicht erfundene geheime Tokens sowie ZimaOS-AppData-Pfade.
- `PUID` und `PGID` führen im neuen Test nicht zu einem automatisch gesetzten Docker-`user:`; die Ursache eines bereits im ursprünglichen Compose enthaltenen `user: 1000:1000` ist damit nicht bewiesen.
- Beta 19–21: Volumebehandlung, Headplane-Konfiguration und Sicherheitsprüfungen bleiben erhalten.

### Grenzen
- Nur sichere, eindeutig belegte Automatik. Das bloße `EXPOSE` eines Docker-Images beweist keine HTTP-Weboberfläche.
- GitHub-CI mit gemockten Quellen ersetzt keinen vollständigen Praxistest mit Drittanbieter-Images auf einem echten ZimaOS-NAS.
- Eine fehlerhafte oder fehlende Konfigurationsdatei oder fehlende Hersteller-Zugangsdaten werden durch die Portautomatik nicht behoben.

### Veröffentlichung
- Version: `0.2.65-beta.22`
- Image: `ghcr.io/isanto1306/install-monitor:0.2.65-beta.22` und nach erfolgreicher Freigabe `:beta`.
- Store-Update erst nach erfolgreichem öffentlichen Image-Abruf.

**Versionsregel:** Nur die aktuelle Beta wird hier dokumentiert.
