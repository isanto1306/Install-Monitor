# Install Monitor – Release Notes

## Version 0.2.56 Beta 6 (19.10.2026)

### Behoben
- HealthLog: Die offizielle Hersteller-Compose mit `${API_TOKEN_HMAC_KEY}` wird bei der Quellanalyse richtig aufgelöst. Das Programm erzeugt einen zufälligen lokalen HMAC-Schlüssel aus 32 Bytes (64 Hexadezimalzeichen).
- Der Schlüssel wird innerhalb eines Compose-Entwurfs einheitlich für die Dienste übernommen, die dieselbe Variable verwenden.
- Bereits eingetragene, konkrete HMAC-Schlüssel werden nicht ersetzt. Bei erneuter Analyse der unveränderten Original-Compose entsteht ein neuer Erstinstallationsentwurf, kein automatisches Update eines bestehenden HealthLog.
- Keine allgemeine Freigabe zur automatischen Erzeugung fremder API-Tokens: Die Sonderbehandlung greift nur bei der veröffentlichten HealthLog-Image-Quelle `ghcr.io/mbombeck/healthlog`.

### Tests
- Regressionstests für Format und konsistente Wiederverwendung des HMAC-Schlüssels im Entwurf.
- Regressionstest: Ein bereits aufgelöster Compose-Entwurf rotiert den HMAC-Schlüssel bei erneuter Variablenauflösung nicht.
- Regressionstest: Bei unbekannten Drittanbieter-Images bleibt eine nicht dokumentierte API-HMAC-Variable ungeklärt.

### Konfiguration beachten
- Nach der Installation den HMAC-Schlüssel nicht ändern: Laut HealthLog-Hersteller würde dies Websitzungen und API-Tokens ungültig machen.
- Auch `ENCRYPTION_KEY` muss dauerhaft gesichert werden. Ein Verlust kann vorhandene verschlüsselte Daten unzugänglich machen.
- `APP_URL` und `NEXT_PUBLIC_APP_URL` müssen zur tatsächlichen Zugriffsadresse passen. Für unverschlüsselten LAN-Zugriff verlangt HealthLog außerdem `SESSION_COOKIE_SECURE=false`; hinter HTTPS korrekt absichern.
- Eine automatische Ermittlung der endgültigen öffentlich erreichbaren HealthLog-Adresse ist nicht implementiert. Sie muss beim Einrichten geprüft werden.

### Veröffentlichung
- Backend, Oberfläche, Docker-Compose-Vorlage, Installationsskript und GitHub-Actions-Workflow auf `0.2.56-beta.6` umgestellt.
- Vorgesehene Container-Tags: `ghcr.io/isanto1306/install-monitor:beta` und `ghcr.io/isanto1306/install-monitor:0.2.56-beta.6`.
- Ein erfolgreicher GHCR-Build und ein echter ZimaOS-Installationstest sind separat zu verifizieren.

**Versionsregel:** Diese Datei enthält ausschließlich die Release Notes der aktuellen Version. Mit jeder neuen Beta werden die vorherigen Hinweise hier ersetzt.
