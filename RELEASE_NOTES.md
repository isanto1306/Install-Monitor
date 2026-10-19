# Install Monitor – Release Notes

## Version 0.2.56 Beta 10 (19.10.2026)

### Behoben: Codeberg-Build bei `image:` und `build:`
- Ein Docker-Compose-Dienst kann zugleich ein Image-Tag und einen lokalen Build-Kontext festlegen. Bisher übersprang Install Monitor in genau diesem Fall die Erzeugung eines überprüfbaren Build-Kontexts.
- Die automatische Analyse erkennt jetzt jedes ausdrücklich angegebene `build:`, unabhängig davon, ob zusätzlich ein `image:` existiert.
- Für direkt analysierte Codeberg-Projekte prüft Install Monitor den Publisher-Commit, vergleicht die geladene Compose mit der Version dieses Commits und fügt den Build-Nachweis `x-install-monitor-codeberg` hinzu.
- Der Originalname `kittygram:latest` wird für den bestätigten lokalen Build durch ein commitgebundenes Image `installmonitor-local/kittygram-kittygram:<12-stelliger-Commit>` ersetzt.
- Derselbe Fehler ist in der GitHub-Build-Vorbereitung behoben. Die ursprüngliche `build:`-Anweisung bleibt bis zum bestätigten lokalen Build im Entwurf enthalten; vor Übergabe an ZimaOS wird sie ordnungsgemäß entfernt.

### Regressionstests
- Durchgängiger Offline-Test des Analyseablaufs eines Codeberg-Projekts mit **beiden** Schlüsseln `image:` und `build:`.
- Überprüfung des lokal erzeugten Image-Namens, der unveränderten Zusatzdienste und des erforderlichen Build-Nachweises.
- GitHub-Test für bereits vorhandene Image-Tags mit `build:`.
- Die vorhandenen Sicherheitsprüfungen für verifizierte Commits, Git LFS, Docker-Build-Bestätigung und private Registry bleiben aktiv.

### Benutzung
- Für Kittygram die originale Projektadresse `https://codeberg.org/irelephant/kittygram` unter **GitHub / URL** neu analysieren. Nicht die alte Compose-Datei aus dem Editor wiederverwenden: Ihr fehlt der verifizierte Build-Kontext aus der Quellanalyse.
- Ein lokaler Build führt fremde Dockerfile-Anweisungen aus und erfordert daher die ausdrückliche Bestätigung vor der Installation.
- Ein erfolgreiches Image-Build beziehungsweise ein ZimaOS-Live-Test wird erst nach separater Überprüfung bestätigt.

### Veröffentlichung
- Backend, Frontend, Dokumentation, Installationsskript, lokale Compose-Vorlage und GitHub-Actions-Workflow auf `0.2.56-beta.10` aktualisiert.
- Vorgesehene GHCR-Tags: `ghcr.io/isanto1306/install-monitor:beta` und `ghcr.io/isanto1306/install-monitor:0.2.56-beta.10`.

**Release-Notes-Regel:** Diese Datei enthält ausschließlich die aktuelle Beta. Bei der nächsten Version wird sie vollständig ersetzt, nicht angehängt.
