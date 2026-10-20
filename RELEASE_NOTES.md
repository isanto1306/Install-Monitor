# Install Monitor – Release Notes

## Version 0.2.57 Beta 14 (20.10.2026)

### Automatische Compose-Vorbereitung
- Explizite, eindeutige Herstellerwerte aus dem Compose-`environment` werden für identische Variablen an anderen Stellen übernommen, statt neue Werte zu erfinden.
- Lokal erzeugbare Kennwörter und Secrets werden pro Variablenname einmal generiert und für abhängige Dienste konsistent wiederverwendet.
- Bei eindeutig vorhandenem, lokalem PostgreSQL-, MySQL- oder MariaDB-Container können nicht gesetzte zugehörige Benutzernamen und Datenbanknamen konservativ ergänzt werden. Keine Remote-Datenbanken, Cloud-/API-Tokens oder unbekannten Pfade raten.
- Externe Zugangsdaten und unbestimmbare Pflichtwerte bleiben sichtbar und müssen bestätigt werden. Fehlende externe Compose-Dateien werden nicht vorgetäuscht.

### Zeitzone vom NAS
- Der Assistent bevorzugt die erkannte ZimaOS/NAS-Zeitzone anstelle eines fest vorgegebenen Orts.
- Ohne erfolgreiche Erkennung bleibt die ursprüngliche Hersteller-Zeitzone erhalten; es wird kein fester Wert unterstellt und eine sonst installierbare Anwendung wird dadurch nicht blockiert.
- Originalwert oder eine manuell gewählte IANA-Zeitzone sind weiterhin ausdrücklich auswählbar.

### Verständliche Installationsdiagnose
- Vollständigere, begrenzte OCI-/runc-/AppArmor-Startfehler erscheinen auch im Installationsprotokoll, statt nur „Docker meldet einen Startfehler“.
- Bekannte Compose-Secrets werden bei der Ausgabe maskiert. Bestehende Host- und Sicherheitsprüfungen bleiben aktiv.

### Veröffentlichung und Grenzen
- Backend, Frontend, Compose-Vorlage, Setup-Skript und GHCR-Metadaten verwenden einheitlich `0.2.57-beta.14`.
- Beta 13 (Docker-Hub-Unterstützung und konservatives ClamAV-Profil) bleibt Bestandteil des Builds.
- Ein GitHub-CI-Durchlauf und ein echter ZimaOS-Installationstest sind unterschiedliche Freigabeschritte. GHCR- und Store-Status separat verifizieren.

**Versionsregel:** Die Release Notes enthalten nur die aktuelle Beta.
