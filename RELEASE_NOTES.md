# Install Monitor – Release Notes

## Version 0.2.56 Beta 12 (19.10.2026)

### Neu: Unterstützung einer öffentlichen Gitea-Quelle
- Die bislang nicht freigegebene Projektadresse `https://gitea.baerentsen.space/FrederikBaerentsen/ComicOPDS` kann jetzt direkt unter **GitHub / URL** analysiert werden.
- Für die öffentliche Gitea-Instanz `gitea.baerentsen.space` werden Repository-Links und direkte Compose-YAML-Dateilinks mit sicherer HTTPS- und Netzwerkprüfung unterstützt. Andere, nicht freigegebene Gitea-Hosts werden weiterhin nicht automatisch abgerufen.
- Install Monitor bestimmt nach Möglichkeit den Gitea-Standardbranch, mit Fallback auf `master` und `main`.
- ComicOPDS: Der Hersteller veröffentlicht ein fertiges Image `gitea.baerentsen.space/frederikbaerentsen/comicopds:latest`. Statt der Quell-Compose mit `build: .` wird das offizielle imagebasierte Compose-Beispiel aus `docs/quickstart.md` bevorzugt. Kein unnötiger lokaler Docker-Build.
- Der im Herstellerbeispiel verwendete Beispiel-Server `192.168.10.10` wird **nicht** als echte NAS-Adresse übernommen: `COMICOPDS_SERVER_BASE` muss vor der Installation konkret gesetzt werden.
- Die Image-Verfügbarkeit wird vor der Installation separat per Registry-Manifest geprüft. Comic-Verzeichnis, Speichervolumes, Port und Anmeldung müssen kontrolliert werden.
- Das Eingabefeld weist in DE, EN, FR, PT und ES auf unterstützte Gitea-Instanzen hin.

### Sicherheit und Grenzen
- Freigegebene öffentliche Gitea-Hosts sind ausdrücklich beschränkt. HTTPS, DNS-Prüfung und Ausschluss nichtöffentlicher IP-Adressen bleiben aktiv.
- Keine automatische Übernahme von unbestätigten Docker-Images oder fremden README-Beispielen.
- Gitea-Projekte, die ausschließlich einen lokalen Build anbieten, benötigen weiterhin einen gesondert verifizierten Build-Kontext; Install Monitor gibt dann eine klare Fehlermeldung aus.
- Beim Fernzugriff auf ComicOPDS sollte dessen optionale Authentifizierung eingerichtet werden. Das offizielle Beispiel enthält zunächst keinen aktiven Zugangsschutz.

### Tests und Veröffentlichung
- Offline-Regressionstests für offizielle ComicOPDS-Compose-Erkennung, Projektzuordnung, Schutz vor unpassenden Hersteller-Images, Host-Allowlist und Abweisung lokaler DNS-Ziele.
- Backend, Oberfläche, Dokumentation, Installationsskript, Compose-Vorlage und GHCR-Workflow auf `0.2.56-beta.12` angeglichen.
- Geplante Tags: `ghcr.io/isanto1306/install-monitor:beta` und `ghcr.io/isanto1306/install-monitor:0.2.56-beta.12`.
- CI-Tests, GHCR-Push und ZimaOS-Installation müssen unabhängig voneinander erfolgreich bestätigt werden.

**Regel:** Diese Datei enthält ausschließlich die aktuellen Release Notes. Bei jeder neuen Beta werden die vorherigen Hinweise ersetzt.
