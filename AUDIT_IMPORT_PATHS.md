# Audit der vier Importwege – Install Monitor

Stand: 2026-10-29. Quellcode: Beta-22-Freigabeversion 0.2.65-beta.22; Praxistests mit realen Drittanbieter-Apps bleiben offen.

## Importwege und Datenquellen

| Import | Portquelle | AppData und Konfiguration | Begrenzung |
|---|---|---|---|
| Docker-Image | passende Hersteller-Compose, Docker-Hub oder Image-Metadaten | Herstellerangaben, sonst deklariertes Image-Volume | EXPOSE allein beweist keine Web-UI; Metadata-Fallback erfordert Überprüfung |
| GitHub/URL | importierte Compose plus dokumentierte Haupt-Weboberfläche | relative Bind-Mounts und benannte Volumes bei Build-Plan-Ziel ZimaOS | Nebendateien des Repos werden nicht automatisch importiert |
| Compose-YAML | expliziter ports-Wert; bei Fehlen nur bestätigter HTTP-Healthcheck | relative Pfade und gemeinsam benannte Volumes | ausdrücklich festgelegte Host-Ports bleiben unangetastet |
| LinuxServer.io Katalog | offizielle interne/externe Pflicht-Ports der API | als Pflicht markierte Volumes; zusätzliche Anforderungen sind manuell zu prüfen | optionale Ports/Volumes werden nicht stillschweigend ergänzt |

iSanto1306 App Store und andere App-Kataloge mit Compose-URL benutzen im Frontend den URL-Import. Der LSIO-Katalog dagegen verwendet einen eigenen Backendpfad (kind=lsio).

## Gemeinsame Verarbeitung nach dem Import

Alle Quellen laufen über build_plan: Profile, Ressourcen und Zeitzone; Umgebungsvariablen und Zugangsdaten; Datenpfadabbildung; Prüfung echter Konfigurationsdateien; ZimaOS-Metadaten und Installationsvoraussetzungen. Vorhandene Docker-Volume-Daten werden nicht ohne ausdrückliche Migration ersetzt.

## Konkrete Abweichungen

1. Bei GitHub-/URL-Importen fehlte bisher die automatische Prüfung auf freie Alternativ-Host-Ports, während der Docker-Image-Weg sie bereits verwendete. Der Branch vereinheitlicht diese Prüfung und verlangt einen tatsächlich getesteten freien Host-Port.
2. Fehlt die komplette ports-Abbildung, ergänzt der Branch sie nur, wenn ein eindeutiger container-lokaler HTTP-Healthcheck den internen TCP-Webport belegt. Falls expose existiert, muss dieser Port übereinstimmen.
3. Datenbanken, Worker, Host-Netzwerk- und Proxy-only-Dienste, nicht ausgewählte Profile und bestehende Portbindungen werden nicht automatisch freigegeben.
4. Unbekannte interne Ports, fehlende Neben-Dateien, Tokens, Headscale-Server und proprietäre Startvoraussetzungen können nicht seriös erraten werden.

## Regressionstests

- tests/test_verified_web_port_autocomplete.py: eindeutige HTTP-Ports, bestehende Bindings, Sonderdienste, Reverse-Proxy-Schutz, URL-Portkonflikte.
- tests/test_four_import_paths_matrix.py: vier Quellen mit gleichem Webport; HTTP-Port-Nachweis in drei Compose-Varianten; nie erfundene API-Tokens; gleiche NAS-Datenpfade für Worker; PUID/PGID ohne erfundenes Docker-user-Feld.
- Bestehende Tests sichern ältere Beta-Funktionen sowie Docker-/ZimaOS-Spezialfälle ab.

## Noch offene externe Tests

- Hersteller-Live-Daten und mehrere echte Apps pro Quelle auf einem Test-NAS vergleichen.
- Monline: Herkunft von user: 1000:1000 im ZimaOS-Compose überprüfen. Das gezeigte Hersteller-Startskript benötigt zunächst erhöhte Rechte; das Problem ist unabhängig von der Portkorrektur.
- Zugänglichkeit per LAN, Reverse Proxy und Firewall verifizieren, ohne bewusst interne Dienste zu exponieren.

Diese Testmatrix nutzt gemockte Quellen und Hostprüfungen. Sie beweist nicht, dass beliebige Drittanbieter-Apps fehlerfrei installiert werden.