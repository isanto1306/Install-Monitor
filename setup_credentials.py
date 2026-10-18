#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Interactive credential setup for Install Monitor (Python 3.10+).

Generates a PBKDF2-SHA256 password hash; never stores the plaintext password.
The session secret is required to sign server-side session cookies. It is
server configuration, never a login form field. Existing files are not
silently overwritten.
"""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile

ROUNDS = 600_000
USER_PATTERN = re.compile(r'[A-Za-z0-9_.-]{3,64}\Z')

def create_password_hash(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError('Das Administratorpasswort muss mindestens 12 Zeichen haben.')
    salt = salt if salt is not None else secrets.token_bytes(16)
    if len(salt) != 16:
        raise ValueError('Invalid salt length')
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ROUNDS)
    return f'pbkdf2_sha256:{ROUNDS}:{salt.hex()}:{digest.hex()}'


def write_configuration(path: Path, username: str, password: str, session_secret: str, *, overwrite: bool = False):
    if not USER_PATTERN.fullmatch(username):
        raise ValueError('Benutzername: 3–64 Zeichen, nur Buchstaben, Zahlen, Punkt, Minus und Unterstrich.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,}', session_secret):
        raise ValueError('Das Session-Secret muss mindestens 32 Zeichen aus Buchstaben, Zahlen, Minus oder Unterstrich enthalten.')
    encoded = create_password_hash(password)
    if path.exists() and not overwrite:
        raise FileExistsError(f'{path} existiert bereits. Kein automatisches Überschreiben.')
    if path.is_symlink():
        raise ValueError('Verknüpfungen als Konfigurationsdatei sind nicht zulässig.')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.im-secret-', dir=path.parent)
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(f'IM_ADMIN_USERNAME={username}\n')
            stream.write(f'IM_ADMIN_PASSWORD_HASH={encoded}\n')
            stream.write(f'IM_SESSION_SECRET={session_secret}\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> int:
    parser = argparse.ArgumentParser(description='Install Monitor: Admin-Zugangsdaten sicher erzeugen')
    parser.add_argument('--output', default='install-monitor.env', help='Lokale ENV-Datei (nicht auf GitHub hochladen)')
    parser.add_argument('--overwrite', action='store_true', help='Explizit vorhandene ENV-Datei ersetzen (meldet alle Nutzer ab)')
    options = parser.parse_args()
    output = Path(options.output).resolve()
    if output.exists() and not options.overwrite:
        parser.error(f'{output} existiert bereits. --overwrite nur bei geplanter Rotation verwenden.')
    print('Install Monitor – Administrator-Einrichtung')
    print('Das Passwort wird verdeckt eingegeben und ausschließlich als Prüfsumme gespeichert.')
    while True:
        username = input('Administrator-Benutzername: ').strip()
        if USER_PATTERN.fullmatch(username):
            break
        print('3–64 Zeichen: Buchstaben, Ziffern, Punkt, Minus oder Unterstrich.')
    while True:
        password = getpass.getpass('Administrator-Passwort (mind. 12 Zeichen): ')
        confirm = getpass.getpass('Passwort wiederholen: ')
        if password != confirm:
            print('Passwörter stimmen nicht überein.')
        elif len(password) < 12:
            print('Das Passwort ist zu kurz.')
        else:
            break
    print('Session-Secret: eigenes Secret (mind. 32 Zeichen) oder leer lassen zum sicheren Generieren.')
    while True:
        supplied = getpass.getpass('Session-Secret (Enter = automatisch): ')
        if not supplied:
            session_secret = secrets.token_urlsafe(48)
            break
        if re.fullmatch(r'[A-Za-z0-9_-]{32,}', supplied):
            session_secret = supplied
            break
        print('Mindestens 32 Zeichen: Buchstaben, Zahlen, Minus oder Unterstrich.')
    write_configuration(output, username, password, session_secret, overwrite=options.overwrite)
    print(f'Konfiguration unter {output} gespeichert (Dateirechte 600).')
    print('Die ENV-Datei muss in der Docker-Konfiguration geladen werden (z. B. env_file).')
    print('Nicht nach GitHub hochladen. Container nach dem Übernehmen neu starten.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
