# Install Monitor – Release Notes

## Version 0.2.59 Beta 16 (20.10.2026)

### Docker Compose Shell-Skripte: doppelte Variablenauswertung verhindern
- Fix für Nametag: Die offizielle ZimaOS-Compose enthält POSIX-Shell-Kommandos mit Compose-Escape-Sequenzen wie `$$secrets`, `$$DB_PASSWORD` und `$$(rand 32)`. Werden diese unterwegs zweimal als Compose-Ausdrücke interpretiert, kann z. B. das Ausgabeziel von `nametag-init` leer werden.
- Beim tatsächlichen ZimaOS-Installationsauftrag werden ausdrücklich deklarierte `sh -c`-/`ash -c`-Array-Skripte mit `$$` vor erneuter Compose-Interpolation geschützt: Einmaliges Auflösen des Compose-Dollar-Escapes und Transport der Shell-Anweisung als POSIX-`printf`-Oktalfolge. Der Transport enthält selbst keine Dollarzeichen.
- Es sind weder zusätzliche Binaries noch zusätzliche Host-Mounts erforderlich. Der Shell-Prozess führt weiterhin die ursprüngliche Herstellerlogik aus.
- Die Vorschau und der Hersteller-Quellcode bleiben unverändert. Andere Befehlstypen werden nicht blind umgeschrieben. Überlange Skripte werden mit einer klaren Fehlermeldung abgelehnt.
- Testabdeckung für Nametag-Initialisierung, Cron-Tokens, reguläre Skripte und wiederholte Compose-Verarbeitung.

### Bestehende Verbesserungen bleiben erhalten
- Offizielle herstellereigene ZimaOS-Compose bevorzugen, externe Docker-Netzwerke vor Installation prüfen und fehlende Netzwerke nicht eigenmächtig erzeugen.
- Einmalige Initialisierungscontainer mit Exit-Code 0 als erfolgreich erkennen, fehlende Container und Images differenziert melden.
- NAS-Zeitzone erkennen statt feste Regionen zu unterstellen; unterstützte Compose-Variablen und lokale Secrets kontrolliert auflösen.

### Veröffentlichung
- Backend, Frontend, Compose-Vorlage, Installer und GHCR-Workflow verwenden `0.2.59-beta.16`.
- Geplante Tags: `ghcr.io/isanto1306/install-monitor:0.2.59-beta.16` und `:beta`.
- Der iSanto1306 ZimaOS App Store wird nach erfolgreicher GHCR-Veröffentlichung synchronisiert.
- Eine GitHub-CI-Prüfung ersetzt keinen tatsächlichen Installationstest auf ZimaOS.

**Versionsregel:** Die Release Notes enthalten nur die aktuelle Beta.
