# Install Monitor – Release Notes

## Version 0.2.64 Beta 21 (24.10.2026)

### Headplane: config.yaml direkt in Install Monitor erstellen
- Wenn bei der offiziellen Headplane-Docker-Vorlage die Konfigurationsdatei `/DATA/AppData/<app>/config.yaml` fehlt, bietet die Prüfansicht jetzt einen gezielten Einrichtungsdialog.
- Der Anwender trägt die tatsächliche, vom Headplane-Container erreichbare Headscale-URL sowie die gewünschte Headplane-Webadresse ein. Die Adressen werden nicht erraten; ein bereits laufender Headscale-Server bleibt Voraussetzung.
- Ein CSRF-geschützter und authentifizierter Backend-Endpunkt erstellt eine minimale, laut offizieller Headplane-Dokumentation gültige `config.yaml` einschließlich eines zufälligen, 32 Zeichen langen `server.cookie_secret`.
- Die Datei wird ausschließlich über einen isolierten Docker-Hilfscontainer unter `/DATA/AppData/<app>/config.yaml` geschrieben. Keine Netzwerkverbindung, kein privilegierter Hostzugriff, keine bestehende Datei wird überschrieben.
- Erstellte Konfigurationsdateien erhalten nur Eigentümerrechte `0600`. Session-Secret und Dateiinhalte erscheinen weder in Logs noch Docker-Kommandoargumenten oder API-Antworten.
- Nach erfolgreicher Dateierstellung wird die normale Installation-vorher-Prüfung erneut ausgeführt. Fehlende oder ungültige Dateien blockieren weiterhin die Installation. Die Dateierstellung selbst startet **keinen** Container.
- Die Oberfläche unterstützt Deutsch, Englisch, Französisch, Portugiesisch und Spanisch.

### Grenzen und Voraussetzungen
- Headplane benötigt **Headscale**, nicht lediglich einen Tailscale-Client.
- `headscale.url` ist der HTTP(S)-Endpunkt des Headscale-Servers (nicht gRPC). Die URL muss vom Headplane-Container erreichbar sein.
- Mit dem Assistenten wird eine minimalistische Konfiguration für die normale Anmeldung erzeugt. Fortgeschrittene Funktionen wie OIDC oder Docker-/DNS-Integration erfordern zusätzliche Einstellungen, API-Schlüssel bzw. weitere Mounts.
- Existiert die Datei bereits, bleibt sie unverändert. Kein automatisches Ändern von Benutzerkonfigurationen und keine Datenmigration.
- Für Umgebungen ohne gültigen erreichbaren Headscale-Server reicht die automatische Konfiguration nicht für eine funktionierende Anwendung aus.
- Ein Live-Installationstest auf einem echten ZimaOS-NAS steht noch aus.

### Unverändert
- Beta 20: offizielle Headplane-Docker-Quelle und relative Datei-Mounts.
- Beta 19: sichere AppData-Zuordnung gewöhnlicher benannter Docker-Volumes.

### Veröffentlichung
- Versionskennung: `0.2.64-beta.21`.
- Container: `ghcr.io/isanto1306/install-monitor:0.2.64-beta.21` und nach erfolgreich geprüftem Publish auch `:beta`.
- App-Store-Synchronisation erst nach erfolgreicher Veröffentlichung und anonymem Image-Pull.

**Versionsregel:** Nur die aktuelle Beta wird hier dokumentiert.
