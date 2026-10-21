# Install Monitor – Release Notes

## Version 0.2.62 Beta 19 (21.10.2026)

### ZimaOS: gemeinsame Docker-Volumes als AppData-Ordner
- Für neue ZimaOS-Installationen werden gewöhnliche benannte Docker-Volumes in gemeinsame Bind-Mounts unter `/DATA/AppData/<app>/<volume>` umgewandelt. Der gewählte app-eigene Unterordner wird berücksichtigt.
- Alle Dienste eines Stacks verwenden für dasselbe Volume exakt denselben Host-Pfad, zum Beispiel RSSMonster mit Hauptdienst, Crawl-Worker und Webhook-Worker.
- Schreibschutz (`read_only` / `:ro`) und Container-Mountziele bleiben erhalten; Kollisionen mit expliziten Bind-Verzeichnissen werden vermieden.
- Umgewandelte Top-Level-Volume-Deklarationen entfallen; spezielle, externe oder treiberkonfigurierte Volumes bleiben erhalten.
- Bereits existierende Docker-Volumes werden nicht automatisch migriert oder ersetzt. Kann die NAS-Docker-Volume-Liste nicht gelesen werden, findet keine automatische Umwandlung statt.
- Die Umwandlung ist auf das Zielsystem ZimaOS begrenzt. Für generisches Docker bleiben benannte Volumes unverändert.
- Die Nachkontrolle prüft bei gemeinsam genutzten AppData-Bind-Mounts, ob die gestarteten Container denselben tatsächlichen Host-Pfad verwenden.
- Regressionstests decken unter anderem RSSMonster mit drei Containern, Schreibschutz, bestehende Volumes, spezielle Optionen, Kollisionen, Prüfausfälle und die Vorschau ab.

### Grenzen
- Bind-Mounts übernehmen im Gegensatz zu neu angelegten Docker-Volumes nicht automatisch Dateien aus dem Image. Anwendungen mit Initialdaten im Image sowie unbekannter UID/GID müssen auf einem echten NAS getestet werden.
- Die Umwandlung bedeutet keine Migration einer vorhandenen Docker-Installation. Daten vor Änderungen sichern.
- Ein Docker-Build und GitHub-Regressionstests ersetzen keinen vollständigen frischen ZimaOS-Installationstest.

### Bestehende Funktionen
- Beta 18: Hersteller-Compose-Fragmente mit eindeutig fehlender `services:`-Zeile ergänzen.
- Beta 17: AppData-Beispielpfade sowie eindeutige vorhandene NAS-Medienmounts zuordnen.
- Beta 16: POSIX-Shell-/Cron-Dollarescaping erhalten.
- Beta 15: Offizielle ZimaOS-Compose-Rezepte, externe Netzwerke und Init-Container berücksichtigen.

### Veröffentlichung
- Backend, Docker-Compose, Installer, Oberfläche und GHCR-Workflow verwenden `0.2.62-beta.19`.
- GHCR: `ghcr.io/isanto1306/install-monitor:0.2.62-beta.19` und `:beta`.
- Der anonyme Image-Pull wird nach erfolgreichem Publish-Workflow separat überprüft.
- Danach kann der iSanto1306 Zima-App-Store synchronisiert werden.

**Versionsregel:** Nur die aktuelle Beta wird hier dokumentiert.
