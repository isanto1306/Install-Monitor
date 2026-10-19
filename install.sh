#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Install Monitor v0.2.56-beta.5 — first-time Docker Compose installation on ZimaOS/Linux.
# Does not delete or upgrade any existing installation. Never prints secrets.
set -eu
umask 077

fail() { printf 'FEHLER: %s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P) || fail 'Projektverzeichnis ist nicht erreichbar.'
cd "$SCRIPT_DIR" || fail 'Projektverzeichnis konnte nicht geöffnet werden.'
MODE=${1:---docker}
case "$MODE" in
    --docker|--check) ;;
    --zimaos) fail 'Direkte ZimaOS-App-Registrierung ist in dieser Beta noch nicht implementiert. Verwende --docker; eine automatische Dashboard-Kachel wird nicht versprochen.' ;;
    *) fail 'Aufruf: sh install.sh [--check|--docker]' ;;
esac

# The runtime registry uses this exact location. No alternate mount root is supported.
STATE_ROOT=/DATA/AppData/Install-Monitor
ENV_FILE="$STATE_ROOT/.env"
[ -f main.py ] && [ -f static/app.js ] && [ -f static/style.css ] && [ -f static/index.html ] && [ -f static/isanto1306-apps-logo.png ] || fail 'Dateien fehlen. Das GitHub-Quellpaket vollständig entpacken.'
[ -f Dockerfile ] && [ -f requirements.txt ] && [ -f docker-compose.yml ] && [ -f setup_credentials.py ] || fail 'Installer- und Compose-Dateien fehlen.'
command -v docker >/dev/null 2>&1 || fail 'Docker wurde nicht gefunden.'
docker compose version >/dev/null 2>&1 || fail 'Docker Compose v2 wurde nicht gefunden.'
command -v python3 >/dev/null 2>&1 || fail 'Python 3 ist für die Einrichtung erforderlich.'

check_credentials() {
    [ -f "$ENV_FILE" ] && [ ! -L "$ENV_FILE" ] || fail 'Die Zugangsdaten-Datei fehlt oder ist ein Symlink.'
    python3 - "$ENV_FILE" <<'PY'
import os, pathlib, re, sys
p=pathlib.Path(sys.argv[1])
if p.stat().st_mode & 0o077:
    raise SystemExit('FEHLER: Die .env-Datei ist für Gruppen/andere Benutzer lesbar. Bitte chmod 600 verwenden.')
values={}
for line in p.read_text(encoding='utf-8').splitlines():
    if not line or line.startswith('#'): continue
    if '=' not in line: raise SystemExit('FEHLER: Ungültige Zeile in .env.')
    key,val=line.split('=',1)
    if key in values: raise SystemExit('FEHLER: Doppelter Schlüssel in .env.')
    values[key]=val
if not re.fullmatch('[A-Za-z0-9_.-]{3,64}',values.get('IM_ADMIN_USERNAME','')):
    raise SystemExit('FEHLER: Bitte IM_ADMIN_USERNAME mit einem gültigen Namen festlegen.')
if not values.get('IM_ADMIN_PASSWORD_HASH') and not values.get('IM_ADMIN_PASSWORD'):
    raise SystemExit('FEHLER: Admin-Passwort/Hash fehlt.')
if len(values.get('IM_SESSION_SECRET','')) < 32:
    raise SystemExit('FEHLER: IM_SESSION_SECRET ist zu kurz (mindestens 32 Zeichen).')
if values.get('IM_DATA_DIR'):
    raise SystemExit('FEHLER: IM_DATA_DIR aus dem alten Installer bitte entfernen; dieser Installer verwendet /app/data.')
PY
}

if [ "$MODE" = '--check' ]; then
    info 'Install Monitor v0.2.56-beta.5 – read-only Vorabprüfung'
    if [ -f "$ENV_FILE" ]; then
        check_credentials
        docker compose -f docker-compose.yml config --quiet || fail 'Compose-Konfiguration ist ungültig.'
        info 'OK: Programmdateien, Zugangsdaten-Format und Compose-Konfiguration geprüft.'
    else
        info "Noch keine privaten Zugangsdaten unter $ENV_FILE (normal vor Ersteinrichtung)."
        info 'Compose-Konfiguration kann ohne diese Datei noch nicht vollständig validiert werden.'
        info 'OK: Programmdateien und Docker-Compose-Werkzeug sind vorhanden. Keine Dateien erzeugt.'
    fi
    exit 0
fi

# Must not silently overwrite, migrate, or restart existing container projects.
docker info >/dev/null 2>&1 || fail 'Docker-Daemon ist nicht erreichbar.'
for container in install-monitor install-monitor-local-registry; do
    if docker container inspect "$container" >/dev/null 2>&1; then
        fail "Container '$container' existiert bereits. Bestehende Installation nicht verändert."
    fi
done
[ -S /var/run/docker.sock ] || fail 'Docker-Socket /var/run/docker.sock fehlt.'
[ -d /DATA/AppData ] || fail '/DATA/AppData fehlt – dieser Installer ist für ZimaOS und kompatible Hosts ausgelegt.'
[ -d /media ] || fail '/media fehlt – benötigter Lesemount kann nicht eingerichtet werden.'
# Abort before touching credentials when either of our reserved ports is in use.
python3 - <<'PYPORTS' || fail 'Die benötigten Ports 9012 oder 50813 sind belegt oder nicht verfügbar.'
import socket
for ip, port in [('0.0.0.0', 9012), ('127.0.0.1', 50813)]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((ip, port))
        except OSError:
            print(f'Port {ip}:{port} ist nicht frei.', flush=True)
            raise SystemExit(1)
PYPORTS
if [ -L "$STATE_ROOT" ]; then fail 'Zielverzeichnis darf kein Symlink sein.'; fi
mkdir -p "$STATE_ROOT" || fail "Zielverzeichnis $STATE_ROOT konnte nicht angelegt werden."
chmod 700 "$STATE_ROOT" || fail 'Zielordner-Rechte konnten nicht gesetzt werden.'
if [ ! -e "$ENV_FILE" ]; then
    [ -t 0 ] || fail 'Ersteinrichtung benötigt ein interaktives Terminal zur sicheren Passworteingabe.'
    info 'Einmalige Administrator-Einrichtung: Benutzername, Passwort, Session-Secret.'
    python3 "$SCRIPT_DIR/setup_credentials.py" --output "$ENV_FILE" || fail 'Zugangsdaten-Einrichtung wurde abgebrochen.'
fi
check_credentials
mkdir -p "$STATE_ROOT/data" "$STATE_ROOT/registry" || fail 'Laufzeitordner konnten nicht angelegt werden.'
chmod 700 "$STATE_ROOT/data" "$STATE_ROOT/registry" || fail 'Laufzeitordner-Rechte konnten nicht gesetzt werden.'
# Never print config expansion: it may contain sensitive environment values.
docker compose -f docker-compose.yml config --quiet || fail 'Compose-Konfiguration ist ungültig.'
info 'Baue Install Monitor v0.2.56-beta.5 lokal (kein Push zu Docker Hub/GitHub) ...'
docker compose -f docker-compose.yml build || fail 'Image-Build fehlgeschlagen; es wurde kein alter Container ersetzt.'
info 'Starte die zwei Compose-Services ...'
docker compose -f docker-compose.yml up -d --no-build || fail 'Containerstart fehlgeschlagen. Logs prüfen.'
# /api/session is intentionally public but exposes no credentials.
n=0
while [ "$n" -lt 30 ]; do
    if docker exec install-monitor python -c 'import json,urllib.request; d=json.load(urllib.request.urlopen("http://127.0.0.1:9012/api/session",timeout=2)); assert d.get("version")=="0.2.56-beta.5"' >/dev/null 2>&1; then
        info 'ERFOLG: Install Monitor v0.2.56-beta.5 läuft. Öffne http://<NAS-IP>:9012 im Heimnetz.'
        info 'Anmeldung: der zuvor festgelegte Benutzername und das Passwort.'
        info 'Docker-Compose-Installation bedeutet noch keine automatische ZimaOS-Dashboard-Kachel.'
        exit 0
    fi
    n=$((n+1))
    sleep 2
done
info 'Die Container wurden gestartet, aber die API antwortet noch nicht korrekt. Letzte Logs:' >&2
docker compose -f docker-compose.yml logs --tail 30 >&2 || true
fail 'Gesundheitsprüfung fehlgeschlagen. Zugangsdaten verbleiben geschützt am Zielpfad.'
