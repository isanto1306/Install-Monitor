# Install Monitor v0.2.56 – Datenschutzprüfung für GitHub-Beta

**Ergebnis:** Dies ist eine bereinigte **Veröffentlichungskopie**. Es wurden keine persönlichen Nutzerdaten von der NAS-Laufzeit übernommen. Noch **kein GitHub-Upload**, kein Realtest auf einem NAS.

## Benutzerentscheidung: öffentliche Angaben bleiben

Das iSanto1306-Logo sowie die im UI gewünschten Projektlinks zu **PayPal**, **GitHub-Profil** und **Instagram** bleiben ausdrücklich unverändert. Diese Angaben sind absichtlich öffentlich und dürfen nicht mit privaten Laufzeitdaten verwechselt werden.

## Ausgeschlossen

Die folgenden privaten Dateitypen bzw. Verzeichnisse aus dem ursprünglichen NAS-Archiv wurden nicht übernommen:

- `.env`, gespeicherte Admin-Zugangsdaten und Session-Secrets
- `data/` inklusive gespeicherter GitHub-Tokens, TOTP-Authenticator-Daten und Reverse-Proxy-Zieladressen
- `registry/` mit Image-Blobs; `tmp/`, lokale Audit-/Logdateien, Caches und Backups
- persönliche NAS-LAN-Adressen und der private NAS-Hostname
- Schlüssel, Datenbanken und sonstige lokale Laufzeitkonfigurationen

`.gitignore`, `.dockerignore` und `scripts/prepublish_check.py` sind nur zusätzliche Schutzmaßnahmen. Vor dem ersten Push müssen auch `git status`, `git ls-files` und die spätere Commit-Historie geprüft werden.

## Gezielte Codeänderungen

- `install.sh` erstellt bei der Erstinstallation eine **lokale**, nicht versionierte Datei `/DATA/AppData/Install-Monitor/.env` über `setup_credentials.py`.
- Benutzername, Passwort und Session-Secret werden abgefragt. Das Passwort wird **nur als Hash** gespeichert; das Secret bleibt in der privaten Datei.
- Private Registry auf Loopback `127.0.0.1:50813`, kein Cloud-Push in diesem Installer.
- Keine öffentlich enthaltene feste NAS-IP; ZimaOS-Integrations-URLs werden nicht auf einen privaten Host voreingestellt.
- `referrer=no-referrer` in der Browseroberfläche verhindert die normale Übertragung der internen Seitenadresse als Referer beim Laden externer Assets.

## Netzwerkverhalten und Restrisiken

- Bei einer vom Nutzer angeforderten Katalogsuche: externe Dienste wie GitHub, GHCR, Docker Hub, LinuxServer.io, selfh.st und CDN-Hosts sehen die jeweilige Anfrage-IP und öffentliche Abfragedaten.
- Wird vom Nutzer ein GitHub-API-Token gespeichert, kann Install Monitor es bei GitHub-API-Anfragen an `api.github.com` senden (notwendiger Teil der Funktion).
- Bei einer Installation werden die dabei eingestellten Compose-/Host-Daten an die ausgewählte ZimaOS-Instanz übermittelt; nicht an GitHub als Veröffentlichung.
- Docker-Socket-Zugriff gewährt weitreichende NAS-Rechte. Die Oberfläche sollte nur im LAN/VPN bzw. hinter einem sicher konfigurierten HTTPS-Reverse-Proxy erreichbar sein.
- Die Code-Prüfung hat keine allgemeine Telemetrie festgestellt. Ein statischer Scan garantiert nicht, dass im Betrieb keinerlei Informationen nach außen gehen.

## Unbedingt vor öffentlicher Veröffentlichung

1. Den im **ursprünglichen privaten ZIP** vorhandenen GitHub-Token bei GitHub widerrufen/ersetzen. Alte ZIP-Datei keinesfalls hochladen.
2. TOTP-Secret und Administrator-Secrets vorsorglich rotieren, falls sie extern offengelegt worden sind.
3. **Erledigt:** Rechteinhaber hat GPL v3 gewählt; vollständige Lizenzdatei und externe Rechtehinweise sind enthalten.
4. Neuinstallation inklusive Docker-Build und ZimaOS-Kompatibilität auf einem **separaten Testsystem** überprüfen.
5. Öffentliche Git-Historie nach dem ersten Commit scannen; keine frühere NAS-Historie importieren.

**Testumfang:** Syntaxprüfungen, YAML- und Quellenprüfung, Anmelde-API-Test, isolierte Shell-/Docker-Mocktests. Ein echter Docker-Daemon war in dieser Arbeitsumgebung nicht verfügbar. Es wurde nichts auf das NAS oder nach GitHub übertragen.
