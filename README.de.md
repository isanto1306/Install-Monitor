# Install Monitor v0.2.56 Beta 12 · öffentliche Beta (GPL v3)

**Neuinstallationen starten auf Englisch.** Eine bereits gewählte Sprache bleibt beim Update erhalten.

Install Monitor unterstützt das Analysieren und Installieren von Docker-Compose-Projekten auf ZimaOS und kompatiblen Linux-/Docker-Hosts. Dieser Quellcode ist **eine GitHub-Veröffentlichungsvorbereitung**. Keine automatische Registrierung einer Dashboard-Kachel, keine Garantie der Kompatibilität jeder Drittanbieter-App.

## Funktionen

- Vier App-Kataloge: iSanto1306, LinuxServer.io, selfh.st, GitHub
- Quellanalyse, Compose-Vorschau, Ports, Pfade und Berechtigungen
- GitHub- und Codeberg-Builds mit festem Commit, Codeberg inklusive kontrollierter Git-LFS-Dateien
- Hardware-/GPU-Erkennung für mehrere Services
- Administrator-Login mit Benutzername und Passwort; signierte Session
- DE / EN / FR / PT / ES
- Optionale GitHub-Integration und lokale Registry für selbst gebaute Images

## Voraussetzungen

- Ein ZimaOS-NAS mit Shell-Zugang und Docker + `docker compose` (v2), alternativ ein entsprechend vorbereitetes Linux-System
- Python 3.10+ für die einmalige sichere Zugangsdaten-Erstellung
- Verfügbarer Port **9012/TCP** (Web-UI) und Loopback-Port **50813/TCP** (private Registry)
- Schreibzugriff auf `/DATA/AppData/Install-Monitor` und bestehende Host-Verzeichnisse `/DATA/AppData`, `/media`
- Docker-Socket `/var/run/docker.sock` (die App kann dadurch Container und Host-Ressourcen verwalten)
- Internetzugang zum Abruf von Docker-Images und optionalen Online-Katalogen

**Sicherheitswarnung:** Der Docker-Socket verleiht der Webanwendung weitreichende Rechte auf dem NAS, auch wenn er als `:ro` eingehängt wird. Install Monitor **nicht direkt über Portfreigaben ins Internet stellen**. Für Fernzugriff VPN oder einen korrekt abgesicherten HTTPS-Reverse-Proxy einsetzen. Ohne HTTPS können Login-Daten im Netz mitgelesen werden. Das interne Registry-Interface ist nur auf `127.0.0.1:50813` gebunden.

## Erstinstallation auf dem NAS

1. **Nur dieses bereinigte Quellcode-Paket** auf dem NAS in einen eigenen, privaten Ordner entpacken (beispielsweise `/DATA/AppData/Install-Monitor/source`). Keine persönlichen `.env`-Dateien in einen öffentlichen Repository-Ordner kopieren.
2. In einem Terminal mit dem Installationsordner als Arbeitsverzeichnis:

```sh
sh install.sh --check
sh install.sh --docker
```

`--check` führt nur eine Vorprüfung aus und legt keine Zugangsdaten/Container an. Falls noch keine private `.env` vorhanden ist, meldet es, dass die endgültige Compose-Konfiguration noch nicht vollständig geprüft werden kann.

`--docker` prüft vorhandene Container und Ports, fragt **interaktiv** nach Benutzername, Passwort (mindestens 12 Zeichen) und Session-Secret (eigener Wert ab 32 Zeichen oder sicher generieren lassen). Das Passwort wird nur als PBKDF2-SHA256-Hash gespeichert. Die Datei entsteht unter `/DATA/AppData/Install-Monitor/.env` mit Dateirechten `0600`. Danach werden Image und Container gestartet. **Es werden keine alten Container überschrieben.**

3. Im Heimnetz `http://<NAS-IP>:9012` öffnen und mit dem selbst festgelegten Benutzernamen und Passwort anmelden.

**Wichtig:** Diese Docker-Compose-Installation erscheint nicht automatisch als native ZimaOS-Dashboard-App. Der alte `--zimaos`-Modus verlangte ein nicht vorhandenes Registrierungsskript und ist deshalb in dieser Beta ausdrücklich deaktiviert. Installation über die ZimaOS-App-Verwaltung ist ein separater späterer Integrationsschritt.

## Zugangsdaten und Aufbewahrung

- `.env` und `data/` **niemals committen**; das mitgelieferte `.gitignore` und `.dockerignore` schützt bei normaler Nutzung, ersetzt aber nicht die Kontrolle von `git status` und der Commit-Historie.
- `IM_SESSION_SECRET` gehört zur Server-Konfiguration, **nicht** zur normalen Anmeldemaske. Ein Austausch meldet vorhandene Sitzungen ab.
- Die private `.env` kann jederzeit **vor** dem ersten Start auch manuell erzeugt werden:

```sh
python3 setup_credentials.py --output /DATA/AppData/Install-Monitor/.env
```

- `docker restart install-monitor` lädt **keine** neuen Compose-Umgebungsvariablen. Bei Änderungen an `.env` müssen Container mit `docker compose up -d --force-recreate --no-build` am Projektstandort neu erstellt werden, nachdem die Konfiguration geprüft wurde.
- Die alte Klartextvariable `IM_ADMIN_PASSWORD` wird für Bestandsinstallationen noch akzeptiert; bei Neuinstallationen den neuen Hash verwenden.

## Installation aktualisieren

Diese Anweisungen gelten nur für eine **bereits vorhandene** Installation. Vorher Compose-Konfiguration und `data/` sichern. Nicht das neue Erstinstallationsskript zur Überschreibung bestehender Container verwenden. Programmdateien gezielt ersetzen und den Container neu starten. Bei geänderten Container-/Environment-Angaben ist ein gesondert geplanter Compose-Rollout nötig.

## Netzwerkzugriffe und Datenschutz

- Bei Katalogabfragen sind ausgehende HTTPS-Verbindungen unter anderem zu GitHub, Docker Hub, GHCR und Icon-/Katalog-CDNs möglich; die Dienste sehen die Anfrage-IP.
- Ein optional vom Nutzer gespeicherter GitHub-Token wird für die entsprechenden GitHub-API-Aufrufe verwendet. Er wird nicht ins Repository geschrieben, sofern `data/` ausgeschlossen bleibt.
- Bei einer **vom Nutzer gestarteten** Installation werden Daten an den **ausgewählten** ZimaOS-Host übermittelt; dies ist keine allgemeine Telemetrie.
- Öffentliche Projektlinks zu PayPal, GitHub und Instagram gehören bewusst zur Projektidentität.
- Die Quelle enthält **keine persönlichen NAS-IP-Adressen, tatsächlichen Admin-Passwörter, Session-Secrets oder gespeicherte TOTP-/GitHub-Tokens**.

## Entwicklerprüfung

```sh
python3 -m unittest discover -s tests -v
python3 scripts/prepublish_check.py
python3 -m py_compile main.py setup_credentials.py
node --check static/app.js
```

`python3 scripts/prepublish_check.py` prüft die bereitgestellten Dateien auf typische Secret-Muster und private IP-Adressen; das ist kein vollständiger Sicherheitsbeweis. Ein wirklicher Docker-Build und ein Installationslauf auf einem **frischen ZimaOS-Testsystem** bleiben vor der ersten Freigabe notwendig.

## Lizenz und Projektlinks

**GNU General Public License Version 3, nur Version 3 (`GPL-3.0-only`).** Der vom Autor freigegebene Quellcode von Install Monitor steht unter der GPL v3. Den vollständigen Lizenztext enthält [`LICENSE`](LICENSE). Fremde Bibliotheken und Logos behalten ihre eigenen Lizenzbedingungen, siehe [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Die Projektlinks zu PayPal, Instagram und dem GitHub-Profil bleiben wie gewünscht erhalten.

**Veröffentlichungsstatus:** GitHub-Beta-Kandidat, noch nicht veröffentlicht. Ein echter Docker-/ZimaOS-Erstinstallationstest steht weiterhin aus.
