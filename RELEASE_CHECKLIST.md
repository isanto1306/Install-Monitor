# Freigabecheckliste v0.2.65-beta.22

## Quellcode und Kompatibilität
- [x] Vier Eingänge in gemeinsamer Regressionstest-Matrix (Docker-Image, GitHub/URL, Compose-YAML, LinuxServer.io-Katalog).
- [x] iSanto1306-Katalog verwendet GitHub-/Compose-URL-Import; Pfad ist dokumentiert.
- [x] Eindeutige interne HTTP-Webports dürfen bei fehlenden Portbindungen automatisch ergänzt werden.
- [x] Vorhandene explizite Portzuordnungen und manuelle YAML-Vorgaben bleiben erhalten.
- [x] Host-Portkonflikte bei automatischen URL-/Image-Importen werden nur bei verifiziert freien Alternativen umgesetzt.
- [x] Proxy-only-Services, Worker, Datenbanken und Host-Netzwerk erhalten keine ungewollte Host-Portfreigabe.
- [x] Gemeinsame AppData-Mounts sowie nicht erfundene Tokens/PUID/PGID in Regressionstests abgedeckt.
- [x] Änderungen aus Beta 19–21 bleiben im vorhandenen Code erhalten.

## Veröffentlichung
- [x] GitHub Source Checks für den Beta-22-Freigabecommit erfolgreich.
- [x] GHCR-Image v0.2.65-beta.22 erfolgreich gebaut und veröffentlicht.
- [x] Öffentlicher anonymer Pull, `:beta`-Gleichheit und Versionslabel geprüft.
- [x] ZimaOS App Store aktualisiert und erzeugte `gh-pages`-Compose-Datei überprüft.

## Ausstehende Praxistests
- [ ] Mehrere echte Docker-Images, GitHub-Projekte, YAML-Dateien und Katalog-Apps auf einem Test-NAS installieren.
- [ ] Reale Proxy-/Firewall-Regeln mit den neuen Webport-Vorschlägen testen.
- [ ] Monline-`user: 1000:1000`: Ursprung und korrekten Start ohne Sicherheitsabsenkung prüfen.
- [ ] Unbekannte Hersteller-Initialdaten, Docker-Rechte und Konfigurationsdateien im Einzelfall kontrollieren.

Keine Installationseinschränkung wird zur Umgehung eines fehlenden Herstellerwerts ausgeschaltet.
