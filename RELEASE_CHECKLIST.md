# Freigabecheckliste v0.2.59

- [x] Installer und Compose verwenden dieselbe Backend-Version 0.2.59.
- [x] Erstinstallation fordert Benutzername, Passwort und sicheres Session-Secret.
- [x] Login-Passwort wird als PBKDF2-Hash gespeichert; Secret ist nicht im Repository.
- [x] Alte Image-Namen, Login-Passwort-Druckausgaben und fehlendes `register_zimaos.py` entfernt.
- [x] Lokale Docker-Registry nur an 127.0.0.1; keine Cloud-Push-Routine im Installer.
- [x] Bestehende Container werden beim Installationsversuch nicht angetastet.
- [x] Privater Quellcode-/Secret-Scan; public author links wie gewünscht beibehalten.
- [ ] Neuer GitHub-Token: zuvor im privaten Originalarchiv vorhandenen PAT widerrufen/rotieren.
- [ ] Authenticator-Secret und Anmelde-Secret gegebenenfalls rotieren.
- [ ] Echte Erstinstallation auf separatem, frischen ZimaOS mit Docker prüfen.
- [ ] In ZimaOS-Kachel/Store-Integration separat testen (nicht Teil von `--docker`).
- [x] GPL v3 durch Rechteinhaber gewählt; `LICENSE` (GPL-3.0-only), Copyright und Third-Party-Hinweise ergänzt.
- [ ] Öffentliche Git-Historie mit Secret-Scanner überprüfen; keine alten Daten committen.
- [ ] Erst danach GitHub-Push und Beta-Tag freigeben.

**Hinweis:** Archiv ist ein Freigabe-**Kandidat**, keine Produktionsempfehlung. Ein Shell-/Compose-Mocktest ersetzt keinen realen Docker-Build.

## GitHub-Repository

- [ ] Eigenes **öffentliches und leeres** Repository `isanto1306/Install-Monitor` anlegen (keine Auto-README oder Git-Historie importieren).
- [ ] Nur den bereinigten Quellcode aus diesem Paket committen, keine privaten NAS-Dateien.
- [ ] Tag `v0.2.59-beta.16` erst setzen, wenn Release-Checks bestanden und Rest-Risiken akzeptiert sind.
