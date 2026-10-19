# Install Monitor – Release Notes

## Version 0.2.56 Beta 5 (19.10.2026)

### Behoben
- Die ZimaOS-Verwaltungsadresse wird auf dem NAS dauerhaft in `/app/data/install-monitor-zimaos-target.json` gespeichert und beim nächsten Anmelden beziehungsweise Installieren automatisch geladen.
- Beim Start einer neuen Installation wird die zuletzt verwendete ZimaOS-Adresse nicht mehr gelöscht.
- Benutzername, Passwort und Authenticator-Code werden **nicht** als Teil dieser Einstellung gespeichert.
- Bei einem freigegebenen Reverse-Proxy-Host verlangt Install Monitor jetzt für **jede Installation** einen aktuellen sechsstelligen Authenticator-Code. Das gilt bewusst auch beim Zugriff im LAN: Nur so lässt sich eine Umgehung über die LAN-Zieladresse oder vom Proxy umgeschriebene Header ausschließen.
- Der zusätzliche Eingabebereich für die interne ZimaOS-Adresse erscheint nur, wenn die eingetragene ZimaOS-Zieladresse tatsächlich einem erlaubten Proxy-Host entspricht.
- Erläuterungen zur ZimaOS-Adresse und zur Proxy-Sicherung in DE, EN, FR, PT und ES aktualisiert.

### Veröffentlichung
- Backend, Oberfläche, Docker-Compose-Vorlage, Installationsskript, Dokumentation und GHCR-Publish-Workflow auf `0.2.56-beta.5` abgeglichen.
- Vorgesehene Image-Tags: `ghcr.io/isanto1306/install-monitor:beta` und `ghcr.io/isanto1306/install-monitor:0.2.56-beta.5`.

### Hinweise
- Diese Änderung schützt den Installationsvorgang. Eine vollständige Zwei-Faktor-Anmeldung am Install Monitor selbst ist damit **nicht** eingerichtet.
- Für wirksamen Fernzugriffsschutz muss der HTTPS-Reverse-Proxy eigenständig korrekt abgesichert sein. Install Monitor darf nicht direkt ungeschützt über das Internet erreichbar sein.
- Ein erfolgreiches GitHub-Actions-Build und ein Live-Test auf ZimaOS müssen zusätzlich bestätigt werden.

**Versionsregel:** Diese Datei enthält nur die aktuelle Version. Bei jeder neuen Beta wird ihr Inhalt ersetzt; ältere Release Notes werden nicht angehängt.
