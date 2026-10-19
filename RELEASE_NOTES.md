# Install Monitor – Release Notes

## Version 0.2.56 Beta 11 (19.10.2026)

### Behoben: Codeberg-Commit-Prüfung
- Nach der Quellanalyse von Projekten mit lokalem Docker-Build, beispielsweise `https://codeberg.org/irelephant/kittygram`, konnte die einzelne Forgejo-API-Abfrage `/commits/{branch}` fehlschlagen. Install Monitor brach dann mit der Meldung „Codeberg-Commit konnte nicht geprüft werden“ ab.
- Für öffentliche Codeberg-Repositories werden zur Ermittlung des unveränderlichen Commits jetzt bis zu drei voneinander unabhängige Wege genutzt:
  1. Forgejo-API `/commits/{branch}`.
  2. Forgejo-API `/branches/{branch}` einschließlich der Commit-ID.
  3. `git ls-remote --exit-code` über HTTPS für exakt `refs/heads/{branch}`, wenn die API nicht verfügbar ist.
- Ein Ergebnis wird nur bei einer gültigen 40-stelligen Git-Commit-ID und passend zugeordnetem Branch akzeptiert.
- Der geladene Compose-Inhalt wird weiterhin mit der Datei aus dem ermittelten Commit abgeglichen; der spätere lokale Checkout muss exakt auf diesem Commit stehen. Es wird **niemals** ein ungeprüfter Branch gebaut.
- Wenn alle Prüfwege scheitern, weist die Fehlermeldung auf die Codeberg-API- und Git-HTTPS-Erreichbarkeit hin, statt die Ursache zu verschleiern. Kein unsicherer automatischer Build wird durchgeführt.

### Tests
- Neue Offline-Regressionstests für den normalen API-Abruf, den alternativen Forgejo-Branch-Endpunkt und den Git-HTTPS-Fallback.
- Tests für falsche Branch-Refs, komplett gescheiterte Prüfungen und Ablehnung unsicherer Branch-Namen.
- Alle bisherigen Build-, Git-LFS- und ZimaOS-Installations-Sicherheitsprüfungen bleiben aktiv.

### Veröffentlichung
- Backend, UI, README-Dateien, Installationsskript, Docker-Compose-Vorlage und GHCR-Workflow auf `0.2.56-beta.11` aktualisiert.
- Ziel-Tags: `ghcr.io/isanto1306/install-monitor:0.2.56-beta.11` und `ghcr.io/isanto1306/install-monitor:beta`.
- Der Erfolg des GitHub-Actions-Laufs und der tatsächliche Kittygram-Build auf dem NAS müssen unabhängig vom Quellcode geprüft werden.

**Versionsregel:** Diese Datei enthält ausschließlich die Hinweise zur aktuellen Beta; ältere Release Notes werden bei jedem Update ersetzt.
