# SPDX-License-Identifier: GPL-3.0-only
"""Install Monitor — guided Docker source analysis and ZimaOS installation."""
from __future__ import annotations

import hmac
import base64
import hashlib
import struct
import io
import posixpath
import stat
import tempfile
import zipfile
import ipaddress
import json
import os
import re
import unicodedata
import shlex
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

VERSION = "0.2.58-beta.15"
STATIC = Path(__file__).parent / "static"
# Existing users without IM_ADMIN_USERNAME may continue signing in as "admin".
# New installations should explicitly configure all three credentials.
ADMIN_USER = os.getenv("IM_ADMIN_USERNAME", "admin").strip()
ADMIN_PASS = os.getenv("IM_ADMIN_PASSWORD", "")  # Legacy deployments only
ADMIN_PASSWORD_HASH = os.getenv("IM_ADMIN_PASSWORD_HASH", "").strip()
SESSION_SECRET = os.getenv("IM_SESSION_SECRET", "")
if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", ADMIN_USER):
    raise RuntimeError("IM_ADMIN_USERNAME must contain 3–64 letters, numbers, '.', '_' or '-'")
if not (ADMIN_PASS or ADMIN_PASSWORD_HASH) or not SESSION_SECRET:
    raise RuntimeError("Set IM_ADMIN_USERNAME, IM_ADMIN_PASSWORD_HASH (or legacy IM_ADMIN_PASSWORD), and IM_SESSION_SECRET")
# Public ZimaOS store templates intentionally contain nonfunctional placeholders.
# Refuse to start with them; older private installations otherwise retain their
# existing legacy password behavior for backward compatibility.
_UNSAFE_DEFAULTS = ("CHANGE_ME", "REPLACE_WITH", "YOUR_PASSWORD", "EXAMPLE_SECRET")
if any(any(marker in value.upper() for marker in _UNSAFE_DEFAULTS)
       for value in (ADMIN_USER, ADMIN_PASS, ADMIN_PASSWORD_HASH, SESSION_SECRET)):
    raise RuntimeError("Replace all example username, password, and session-secret placeholders before installation")
if os.getenv("IM_ENFORCE_CREDENTIAL_POLICY", "false").lower() == "true":
    if not ADMIN_PASSWORD_HASH and len(ADMIN_PASS) < 12:
        raise RuntimeError("IM_ADMIN_PASSWORD must contain at least 12 characters")
    if len(SESSION_SECRET) < 32:
        raise RuntimeError("IM_SESSION_SECRET must contain at least 32 characters")
# Validate credential configuration at start, not after an attempted login.
_PASSWORD_HASH_PATTERN = re.compile(r"^pbkdf2_sha256:([0-9]{6,7}):([a-f0-9]{32}):([a-f0-9]{64})$")
if ADMIN_PASSWORD_HASH:
    _match = _PASSWORD_HASH_PATTERN.fullmatch(ADMIN_PASSWORD_HASH)
    if not _match or not 200_000 <= int(_match.group(1)) <= 2_000_000:
        raise RuntimeError("Invalid IM_ADMIN_PASSWORD_HASH; use setup_credentials.py")
if ADMIN_PASSWORD_HASH and len(SESSION_SECRET) < 32:
    raise RuntimeError("IM_SESSION_SECRET must be at least 32 characters long when using the new credential setup")


def _admin_password_valid(candidate: str) -> bool:
    if not ADMIN_PASSWORD_HASH:
        return hmac.compare_digest(candidate.encode('utf-8'), ADMIN_PASS.encode('utf-8'))
    match = _PASSWORD_HASH_PATTERN.fullmatch(ADMIN_PASSWORD_HASH)
    iterations, salt, expected = int(match.group(1)), bytes.fromhex(match.group(2)), bytes.fromhex(match.group(3))
    actual = hashlib.pbkdf2_hmac('sha256', candidate.encode('utf-8'), salt, iterations)
    return hmac.compare_digest(actual, expected)

app = FastAPI(title="Install Monitor", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, https_only=os.getenv("IM_COOKIE_SECURE", "false").lower() == "true", same_site="lax", max_age=int(os.getenv("IM_SESSION_MAX_AGE", "2592000")))
app.mount("/static", StaticFiles(directory=STATIC), name="static")

# Remove the obsolete credentials file from earlier installations.
# Never follow links or remove directories. Failure is nonfatal so read-only
# /app/data mounts do not prevent the application from starting.
def _remove_obsolete_credentials() -> None:
    obsolete = Path('/app/data/install-monitor-ai.json')
    try:
        if obsolete.is_file() and not obsolete.is_symlink():
            obsolete.unlink()
    except OSError:
        pass

_remove_obsolete_credentials()


# Optional GitHub API token. Read only for api.github.com, never raw URLs.
# A separately mounted /app/data volume preserves the token across container upgrades.
_GH_SETTINGS_FILE = Path('/app/data/install-monitor-github.json')
_GH_LOCK = threading.RLock()
_GH_TEST_INFO: dict[str, Any] = {}
_GH_PAT = re.compile(r'^[A-Za-z0-9_-]{20,300}$')

class GitHubTokenChange(BaseModel):
    token: str = Field(min_length=20, max_length=300)


def _gh_saved_token() -> str:
    try:
        if _GH_SETTINGS_FILE.is_symlink() or not _GH_SETTINGS_FILE.is_file():
            return ''
        if _GH_SETTINGS_FILE.stat().st_size > 2048:
            return ''
        obj = json.loads(_GH_SETTINGS_FILE.read_text(encoding='utf-8'))
        token = obj.get('token', '') if isinstance(obj, dict) else ''
        return token if isinstance(token, str) and _GH_PAT.fullmatch(token) else ''
    except (OSError, ValueError, TypeError):
        return ''


def _gh_token() -> str:
    with _GH_LOCK:
        saved = _gh_saved_token()
        if saved:
            return saved
        env = os.getenv('IM_GITHUB_TOKEN', '') or os.getenv('GITHUB_TOKEN', '')
        return env.strip() if _GH_PAT.fullmatch(env.strip()) else ''


def _gh_store(token: str) -> None:
    if not _GH_PAT.fullmatch(token):
        raise HTTPException(400, 'Ungültiges GitHub-Token-Format.')
    import tempfile
    with _GH_LOCK:
        tmpname = None
        try:
            _GH_SETTINGS_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd, tmpname = tempfile.mkstemp(dir=_GH_SETTINGS_FILE.parent, prefix='.im-gh-', suffix='.tmp')
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'token': token}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(tmpname, 0o600)
            os.replace(tmpname, _GH_SETTINGS_FILE)
            _GH_TEST_INFO.clear()
            # Drop icon cache after switching credentials.
            if '_ICON_SCAN_CACHE' in globals():
                with _ICON_SCAN_LOCK:
                    _ICON_SCAN_CACHE.clear()
        except OSError as exc:
            raise HTTPException(500, 'GitHub-Token konnte nicht unter /app/data gespeichert werden.') from exc
        finally:
            if tmpname and os.path.exists(tmpname):
                os.unlink(tmpname)


def _gh_status() -> dict:
    with _GH_LOCK:
        saved = bool(_gh_saved_token())
        source = 'gespeichert' if saved else 'umgebung' if _gh_token() else 'keiner'
        return {'configured': source != 'keiner', 'source': source, **dict(_GH_TEST_INFO)}


@app.get('/api/github/settings')
def github_settings(req: Request):
    require_auth(req)
    return _gh_status()


@app.post('/api/github/settings')
def github_settings_save(req: Request, data: GitHubTokenChange):
    require_write(req)
    _gh_store(data.token.strip())
    return _gh_status()


@app.post('/api/github/remove')
def github_settings_remove(req: Request):
    require_write(req)
    with _GH_LOCK:
        try:
            _GH_SETTINGS_FILE.unlink(missing_ok=True)
        except OSError as exc:
            raise HTTPException(500, 'Gespeichertes GitHub-Token konnte nicht entfernt werden.') from exc
        _GH_TEST_INFO.clear()
    return _gh_status()


@app.post('/api/github/test')
def github_connection_test(req: Request):
    require_write(req)
    if not _gh_token():
        raise HTTPException(400, 'Zuerst einen GitHub-API-Token speichern.')
    # GitHub API /user checks that the credential is accepted; /rate_limit
    # returns the current quota without a separate API search.
    user = _github_json('https://api.github.com/user')
    login = user.get('login')
    if not isinstance(login, str) or not login:
        raise HTTPException(502, 'GitHub hat keine gültige Kontoidentität zurückgegeben.')
    rate = _github_json('https://api.github.com/rate_limit')
    core = (rate.get('resources') or {}).get('core') if isinstance(rate.get('resources'), dict) else None
    if not isinstance(core, dict):
        core = (rate.get('rate') or {}) if isinstance(rate.get('rate'), dict) else {}
    with _GH_LOCK:
        _GH_TEST_INFO.update({'login': login, 'limit': core.get('limit'),
                              'remaining': core.get('remaining'), 'reset': core.get('reset')})
    return _gh_status()


SLUG = re.compile(r"^[a-z][a-z0-9-]{1,42}[a-z0-9]$")
IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@:-]{1,240}$")
ENV_VAR = re.compile(r"\$\{[^}]+\}")
RESERVED = {22, 80, 139, 443, 445, 1910, 3702, 5355, 7681, 8200, 9527, 9993, 11010, 9012, 50813}
PRIVILEGED_KEYS = ("privileged", "pid", "ipc", "devices", "cap_add", "network_mode")
LOGINS: dict[str, int] = {}


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class Source(BaseModel):
    kind: str
    value: str = Field(min_length=1, max_length=524288)
    container_port: int | None = Field(default=None, ge=1, le=65535)
    host_port: int | None = Field(default=None, ge=1, le=65535)
    config_path: str = Field(default="", max_length=180)


class ProjectIconSearch(BaseModel):
    project_url: str = Field(min_length=1, max_length=512)
    refresh: bool = False


class IconCatalogSearch(BaseModel):
    # Only names already parsed from the publisher's Compose or OCI image,
    # plus an optional user-entered search phrase, are sent to the index.
    terms: list[str] = Field(default_factory=list, max_length=16)
    query: str = Field(default="", max_length=90)
    project_url: str = Field(default="", max_length=512)
    refresh: bool = False
    source: str = Field(default='all', pattern=r'^(all|project|dashboardicons|selfhst|simpleicons|techicons)$')


class ServiceResources(BaseModel):
    # None = do not change the upstream Compose limit.
    memory_mb: int | None = Field(default=None, ge=64, le=262144)
    cpu_cores: int | None = Field(default=None, ge=1, le=256)
    gpu: str = Field(default='none', pattern=r'^(none|amd|intel|nvidia)$')


class Plan(BaseModel):
    source: str = Field(min_length=1, max_length=524288)
    name: str = Field(min_length=3, max_length=44)
    title: str = Field(min_length=1, max_length=120)
    icon: str = Field(default="", max_length=1024)
    data_dir: str = Field(default="", max_length=500)
    category: str = Field(default="Others", max_length=40)
    selected_profiles: list[str] = Field(default_factory=list, max_length=20)
    setup_later_profiles: list[str] = Field(default_factory=list, max_length=20)
    tailscale_auth_key: str = Field(default="", max_length=2048)
    cloudflare_tunnel_token: str = Field(default="", max_length=2048)
    resources: dict[str, ServiceResources] = Field(default_factory=dict)
    target_system: str = Field(default="zimaos", pattern=r"^(zimaos|casaos|docker)$")
    timezone_mode: str = Field(default="nas", pattern=r"^(original|nas|manual)$")
    timezone_name: str = Field(default="", max_length=90)
    timezone_add_missing: bool = False


class TimezoneLookup(BaseModel):
    source: str = Field(min_length=1, max_length=524288)


class Install(BaseModel):
    compose: str = Field(min_length=1, max_length=524288)
    host: str = Field(min_length=1, max_length=256)
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024)
    confirmed: bool = False
    build_confirmed: bool = False
    totp_code: str = Field(default="", max_length=8)
    # Optional LAN endpoint when a public, allowlisted proxy hostname is used.
    # Never stored or passed to the installation job status/UI.
    internal_host: str = Field(default="", max_length=256)
    target_system: str = Field(default="zimaos", pattern=r"^(zimaos|casaos|docker)$")


class SourceImageReplacement(BaseModel):
    source: str = Field(min_length=1, max_length=524288)
    service: str = Field(min_length=1, max_length=70)
    expected_image: str = Field(min_length=1, max_length=241)
    replacement_image: str = Field(min_length=1, max_length=241)


class PortScan(BaseModel):
    source: str = Field(min_length=1, max_length=524288)
    selected_profiles: list[str] = Field(default_factory=list, max_length=20)


class ChangePort(PortScan):
    service: str = Field(min_length=1, max_length=70)
    index: int = Field(ge=0, le=99)
    new_port: int = Field(ge=1, le=65535)


class Check(BaseModel):
    internal_host: str = Field(default="", max_length=256)
    host: str = Field(min_length=1, max_length=256)
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024)
    name: str = Field(min_length=3, max_length=44)


def require_auth(req: Request) -> None:
    if not req.session.get("authenticated"):
        raise HTTPException(401, "Bitte zuerst bei Install Monitor anmelden.")


def require_write(req: Request) -> None:
    require_auth(req)
    if not hmac.compare_digest(req.headers.get("X-IM-CSRF", ""), str(req.session.get("csrf", ""))):
        raise HTTPException(403, "Ungültiges Sicherheitstoken. Bitte neu anmelden.")
    # Browsers add Sec-Fetch-Site themselves. This is the most reliable signal
    # that a relative /api/* fetch came from the displayed Install Monitor page.
    # ZimaOS or HTTPS reverse proxies can change Host/scheme before Uvicorn
    # receives the request; comparing the public Origin to req.base_url alone
    # incorrectly rejected legitimate requests behind those proxies.
    origin = req.headers.get("origin")
    if origin:
        try:
            submitted = urllib.parse.urlsplit(origin)
            valid_origin = (submitted.scheme in ("http", "https")
                            and bool(submitted.netloc) and bool(submitted.hostname)
                            and not submitted.username and not submitted.password
                            and submitted.path in ("", "/")
                            and not submitted.query and not submitted.fragment)
        except ValueError:
            valid_origin = False
        if not valid_origin:
            raise HTTPException(403, "Ungültiger Ursprung.")
        actual = urllib.parse.urlsplit(str(req.base_url))
        same_public_origin = (submitted.scheme, submitted.netloc) == (actual.scheme, actual.netloc)
        fetch_site = req.headers.get("sec-fetch-site", "").lower()
        if fetch_site in ("same-site", "cross-site"):
            raise HTTPException(403, "Ungültiger Ursprung.")
        browser_same_origin = fetch_site == "same-origin"
        # A browser cannot set/falsify Sec-Fetch-* from JavaScript. Keep the
        # per-session CSRF token mandatory even when this header is present.
        if not (same_public_origin or browser_same_origin):
            raise HTTPException(403, "Ungültiger Ursprung.")


# Read-only NAS folder browser. Only /DATA and /media are exposed by the
# optional Compose override. The API never reads or returns file contents.
_BROWSE_MOUNT = Path('/im-browse')
_BROWSE_ROOTS = ('/DATA', '/media')
_CREDENTIAL_KEY = re.compile(r"(?:^|_)(?:USER|USERNAME|PASSWORD|PASSWD|SECRET|SECRET_KEY|MASTER_KEY|ENCRYPTION_KEY|JWT_SECRET)$", re.I)
_SECRET_KEY = re.compile(r"(?:^|_)(?:PASSWORD|PASSWD|SECRET|SECRET_KEY|MASTER_KEY|ENCRYPTION_KEY|JWT_SECRET)$", re.I)


class BrowseFolders(BaseModel):
    path: str = Field(default='', max_length=500)


class ComposeAccess(BaseModel):
    source: str = Field(min_length=1, max_length=524288)
    service: str = Field(min_length=1, max_length=70)
    mode: str = Field(pattern=r"^(automatic|normal|root|custom|mount)$")
    uid: int = Field(default=1000, ge=0, le=2147483647)
    gid: int = Field(default=1000, ge=0, le=2147483647)
    index: int = Field(default=-1, ge=-1, le=100)
    read_only: bool = True


class ComposeAppUrl(BaseModel):
    source: str = Field(min_length=1, max_length=524288)
    service: str = Field(min_length=1, max_length=70)
    key: str = Field(min_length=1, max_length=128)
    value: str = Field(min_length=1, max_length=2048)


_APP_URL_KEYS = frozenset(('AUTH_URL', 'APP_URL', 'PUBLIC_URL', 'BASE_URL',
                           'NEXTAUTH_URL', 'SITE_URL', 'ROOT_URL', 'EXTERNAL_URL', 'WEB_URL'))
_APP_URL_PLACEHOLDER = re.compile(r'(your[-_. ]?(?:domain|host|url)|example\.(?:com|org|net)|localhost|127\.0\.0\.1|<[^>]+>)', re.I)


def _app_url_values(doc: dict) -> list[dict]:
    found = []
    for service_name, service in doc['services'].items():
        env = service.get('environment') or {}
        if isinstance(env, dict):
            fields = env.items()
        elif isinstance(env, list):
            fields = (entry.split('=', 1) for entry in env if isinstance(entry, str) and '=' in entry)
        else:
            continue
        for key, value in fields:
            if isinstance(key, str) and key.upper() in _APP_URL_KEYS:
                found.append({'service': service_name, 'key': key, 'value': str(value or ''),
                              'required': _app_url_invalid(str(value or ''))})
    return found[:80]


def _app_url_invalid(value: str) -> bool:
    if not value or _APP_URL_PLACEHOLDER.search(value):
        return True
    try:
        parsed = urllib.parse.urlsplit(value)
        return (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or bool(parsed.username or parsed.password) or bool(parsed.fragment)
                or any(ord(c) < 32 or ord(c) == 127 for c in value)
                or len(value) > 2048 or not (1 <= (parsed.port or 80) <= 65535))
    except ValueError:
        return True


def _app_url_issues(doc: dict) -> list[str]:
    return [f"{item['service']}: {item['key']} benötigt die tatsächliche App-Adresse (keinen Platzhalter)."
            for item in _app_url_values(doc) if item['required'] and not doc['services'][item['service']].get('profiles')]


class ComposeEdit(BaseModel):
    source: str = Field(min_length=1, max_length=524288)
    action: str = Field(pattern=r'^(environment|mount)$')
    service: str = Field(min_length=1, max_length=70)
    key: str = Field(default='', max_length=128)
    index: int = Field(default=-1, ge=-1, le=100)
    value: str = Field(default='', max_length=2048)
    generate: bool = False
    length: int = Field(default=0, ge=0, le=128)  # 0 = typabhängiger Standard
    lowercase: bool = True
    uppercase: bool = True
    digits: bool = True
    symbols: bool = False


def _generate_credential(length: int, lowercase: bool, uppercase: bool,
                         digits: bool, symbols: bool) -> str:
    """Cryptographic generator: at least one character per selected class.

    Avoid '$' because Docker Compose interpolates it, and avoid ':' / quotes
    because credentials are also used in connection strings and CLI contexts.
    """
    groups = []
    if lowercase: groups.append('abcdefghijklmnopqrstuvwxyz')
    if uppercase: groups.append('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    if digits: groups.append('0123456789')
    if symbols: groups.append('!@#%&*_-+=.?')
    if not groups:
        raise HTTPException(400, 'Mindestens eine Zeichenart auswählen.')
    if length < max(12, len(groups)) or length > 128:
        raise HTTPException(400, 'Ungültige Passwortlänge (12–128 Zeichen).')
    alphabet = ''.join(groups)
    chars = [secrets.choice(group) for group in groups]
    chars.extend(secrets.choice(alphabet) for _ in range(length - len(chars)))
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return ''.join(chars)


# v0.2.24: choose the manufacturer's exact format where it is documented.
# The standard UI lengths apply to *local* credentials, not external tokens.
def _im_credential_spec(key: str, doc: dict | None = None) -> dict:
    normalized = key.upper()
    is_rssmonster = bool(doc and (
        str(doc.get('name', '')).lower().startswith('rssmonster')
        or any('rssmonster/rssmonster' in str(svc.get('image', '')).lower()
               for svc in (doc.get('services') or {}).values())))
    if normalized == 'WATCHTOWER_HTTP_API_TOKEN' and doc and any(
        'watchtower' in str(svc.get('image', '')).lower().rsplit('/', 1)[-1]
        for svc in (doc.get('services') or {}).values() if isinstance(svc, dict)
    ):
        # A local Watchtower instance is the authority for this token. Unlike
        # cloud-provider API keys, it is created locally and shared with the
        # Scrypted webhook client. Other API/TOKEN names stay external.
        return {'mode': 'hex', 'length': 64, 'fixed': False}
    if re.search(r'(?:^|_)(?:API|ACCESS|OAUTH|OIDC|CLOUDFLARE|TUNNEL|TS)_?(?:TOKEN|KEY|SECRET)$', normalized):
        return {'mode': 'external', 'length': 0, 'fixed': True}
    if is_rssmonster and normalized == 'ENCRYPTION_KEY':
        # Upstream requires exactly 32 random bytes, Base64-encoded (44 chars).
        return {'mode': 'rssmonster_base64_32', 'length': 44, 'fixed': True}
    if normalized.endswith(('_PASSWORD', '_PASSWD')) or normalized in ('PASSWORD', 'PASSWD', 'DB_PASS'):
        return {'mode': 'password', 'length': 24, 'fixed': False}
    if normalized.endswith(('_SECRET', '_SECRET_KEY', '_MASTER_KEY', '_PRIVATE_KEY')) or normalized in ('SECRET', 'SECRET_KEY', 'MASTER_KEY'):
        return {'mode': 'hex', 'length': 64, 'fixed': False}
    if normalized.endswith('_KEY') and normalized not in ('API_KEY', 'SSH_PUBLIC_KEY'):
        return {'mode': 'hex', 'length': 64, 'fixed': False}
    # External API tokens are never generated by this local password generator.
    return {'mode': 'password', 'length': 24, 'fixed': False}


def _im_generate_local_secret(key: str, doc: dict, *, length: int | None = None,
                              lowercase: bool = True, uppercase: bool = True,
                              digits: bool = True, symbols: bool = False) -> str:
    spec = _im_credential_spec(key, doc)
    if spec['mode'] == 'external':
        raise HTTPException(400, 'Externe API- oder Auth-Tokens müssen vom jeweiligen Anbieter stammen.')
    if spec['mode'] == 'rssmonster_base64_32':
        if length not in (None, 44):
            raise HTTPException(400, 'RSSMonster ENCRYPTION_KEY: festes Format Base64 aus 32 Bytes (44 Zeichen).')
        return base64.b64encode(secrets.token_bytes(32)).decode('ascii')
    count = spec['length'] if length is None else length
    if spec['mode'] == 'hex':
        if count % 2 or not 12 <= count <= 128:
            raise HTTPException(400, 'Hex-Schlüssellänge muss gerade und zwischen 12 und 128 sein.')
        return secrets.token_hex(count // 2)
    return _generate_credential(count, lowercase, uppercase, digits, symbols)


def _im_environment_entries(service: dict) -> dict[str, str]:
    env = service.get('environment') or {}
    if isinstance(env, dict):
        return {str(key): str(value or '') for key, value in env.items()}
    if isinstance(env, list):
        return {entry.split('=', 1)[0]: entry.split('=', 1)[1] for entry in env
                if isinstance(entry, str) and '=' in entry}
    return {}


def _im_shared_credential_services(doc: dict, service: str, key: str) -> list[str]:
    """Share an exact variable name when values agree or are blank.

    Never combine different explicit secrets; they may represent distinct trust
    domains.  One key in multiple services is normally a shared Compose value.
    """
    current = _im_environment_entries(doc['services'][service])
    if key not in current:
        raise HTTPException(404, 'Umgebungsvariable nicht vorhanden.')
    holders = [(name, _im_environment_entries(svc)[key])
               for name, svc in doc['services'].items()
               if key in _im_environment_entries(svc)]
    present = {value for _, value in holders if value}
    if len(present) > 1:
        return [service]
    return [name for name, _ in holders]


def _im_credential_mismatch_warnings(doc: dict) -> list[str]:
    entries: dict[str, dict[str, str]] = {}
    for name, svc in doc['services'].items():
        for key, value in _im_environment_entries(svc).items():
            if _SECRET_KEY.search(key) and value:
                entries.setdefault(key, {})[name] = value
    return [f'Variable {key} besitzt unterschiedliche Werte in den Diensten '
            + ', '.join(sorted(services)) + '. Bitte absichtlich getrennte Werte bestätigen.'
            for key, services in entries.items() if len(set(services.values())) > 1]


def _required_credentials(doc: dict) -> list[tuple[str, str]]:
    """Reject empty local login credentials, not optional external API keys."""
    missing = []
    for svc_name, svc in doc.get('services', {}).items():
        # Unselected profile services are not installed by default.
        if svc.get('profiles'):
            continue
        for item in _credential_fields({'services': {svc_name: svc}}):
            key = item['key'].upper()
            if (not item['value'].strip() and (
                key.endswith(('_PASSWORD', '_PASSWD', '_SECRET_KEY', '_MASTER_KEY', '_ENCRYPTION_KEY', '_JWT_SECRET'))
                or key in ('PASSWORD', 'SECRET_KEY', 'MASTER_KEY')
            ) and not key.startswith(('OIDC_', 'OAUTH_', 'WEBHOOK_', 'TUNNEL_', 'TS_'))
                and key not in ('ADMIN_PASSWORD',)):
                missing.append((svc_name, item['key']))
    return missing


def _browse_path(hostpath: str) -> Path:
    # The explicit root mapping must not be bypassed via .., symlinks, or /etc.
    if not hostpath or hostpath == '/':
        raise HTTPException(400, 'Bitte einen freigegebenen NAS-Ordner auswählen.')
    if (not hostpath.startswith('/') or len(hostpath) > 500
            or any(ord(c) < 32 or ord(c) == 127 for c in hostpath)
            or ':' in hostpath or '\\' in hostpath
            or any(seg in ('.', '..') for seg in hostpath.split('/'))):
        raise HTTPException(400, 'Ungültiger NAS-Ordner.')
    root = next((r for r in _BROWSE_ROOTS if hostpath == r or hostpath.startswith(r + '/')), None)
    if not root:
        raise HTTPException(403, 'Zugriff nur auf freigegebene Ordner unter /DATA und /media.')
    physical_root = _BROWSE_MOUNT / root.lstrip('/')
    if not physical_root.is_dir() or physical_root.is_symlink():
        raise HTTPException(503, 'Ordnerfreigabe fehlt. docker-compose.override.yml einspielen und Install Monitor neu erstellen.')
    rel = hostpath[len(root):].strip('/')
    target = physical_root
    for part in filter(None, rel.split('/')):
        target = target / part
        if target.is_symlink():
            raise HTTPException(403, 'Symbolische Verknüpfungen dürfen nicht geöffnet werden.')
    try:
        if os.path.commonpath((str(physical_root.resolve()), str(target.resolve(strict=True)))) != str(physical_root.resolve()):
            raise HTTPException(403, 'Verzeichnis liegt außerhalb der Freigabe.')
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(404, 'NAS-Verzeichnis nicht gefunden.') from exc
    if not target.is_dir():
        raise HTTPException(404, 'NAS-Verzeichnis nicht gefunden.')
    return target


def _credential_fields(doc: dict) -> list[dict]:
    fields = []
    for svcname, service in doc['services'].items():
        env = service.get('environment') or {}
        if isinstance(env, dict):
            items = env.items()
        elif isinstance(env, list):
            items = [entry.split('=', 1) for entry in env if isinstance(entry, str) and '=' in entry]
        else:
            continue
        for key, val in items:
            if not isinstance(key, str) or not _CREDENTIAL_KEY.search(key):
                continue
            fields.append({'service': svcname, 'key': key, 'value': str(val or ''),
                           'spec': _im_credential_spec(key, doc),
                           'secret': bool(_SECRET_KEY.search(key)),
                           'required': not bool(val) and not bool(service.get('profiles'))
                           and (key.upper().endswith(('_PASSWORD', '_PASSWD', '_SECRET_KEY', '_MASTER_KEY', '_ENCRYPTION_KEY', '_JWT_SECRET'))
                                or key.upper() in ('PASSWORD', 'SECRET_KEY', 'MASTER_KEY'))
                           and not key.upper().startswith(('OIDC_', 'OAUTH_', 'WEBHOOK_', 'TUNNEL_', 'TS_'))
                           and key.upper() != 'ADMIN_PASSWORD'})
    # Render shared keys only once. The representative has an array of target
    # services; compose_modify writes the same value to each one atomically.
    output = []
    seen: set[str] = set()
    for field in fields:
        key = field['key']
        if key in seen:
            continue
        targets = _im_shared_credential_services(doc, field['service'], key)
        if len(targets) >= 2:
            instances = [item for item in fields if item['key'] == key and item['service'] in targets]
            selected = next((item for item in instances if item['value']), instances[0])
            selected = dict(selected)
            selected['services'] = targets
            selected['required'] = any(item['required'] for item in instances)
            output.append(selected)
            seen.add(key)
        else:
            output.append(field)
    return output[:80]


# v0.2.43: Sample paths from manufacturer README files are NOT host paths.
# Never create /path on the read-only ZimaOS root, and never silently replace
# a required config file with a nonexistent placeholder under AppData.
_IM_EXAMPLE_HOST_PREFIXES = ('/path/to/', '/your/path/', '/path/on/host/', '/your/host/path/')


def _im_example_host_path(source: str) -> bool:
    return isinstance(source, str) and source.lower().startswith(_IM_EXAMPLE_HOST_PREFIXES)


def _im_sample_mount_issues(doc: dict) -> list[str]:
    result = []
    for svc_name, service in doc.get('services', {}).items():
        if not isinstance(service, dict):
            continue
        if service.get('profiles'):
            continue
        for entry in service.get('volumes') or []:
            if isinstance(entry, str):
                parts = entry.split(':', 2)
                if len(parts) < 2: continue
                source, target = parts[:2]
            elif isinstance(entry, dict) and entry.get('type') == 'bind':
                source, target = str(entry.get('source') or ''), str(entry.get('target') or '')
            else:
                continue
            if not _im_example_host_path(source):
                continue
            kind = 'Datei' if _im_file_mount_expected(source, target) else 'Ordner'
            invalid = 'keine echte NAS-Datei' if kind == 'Datei' else 'kein echter NAS-Ordner'
            result.append(f'{svc_name}: Hersteller-Beispielpfad {source} ist {invalid}. '
                          f'Unter Zugangsdaten und NAS-Freigaben eine echte Quelle unter /DATA/AppData/... für {target} auswählen. '
                          + ('Die Konfigurationsdatei muss vorher wirklich existieren; sie wird nicht automatisch erzeugt.'
                             if kind == 'Datei' else 'Der Zielordner kann vor der Installation angelegt werden.'))
    return result[:30]


def _mount_fields(doc: dict) -> list[dict]:
    mounts = []
    for svcname, service in doc['services'].items():
        for idx, item in enumerate(service.get('volumes') or []):
            if isinstance(item, str):
                src = item.split(':', 1)[0]
                dest = item.split(':', 2)[1] if ':' in item else ''
            elif isinstance(item, dict) and item.get('type') == 'bind':
                src, dest = item.get('source'), item.get('target')
            else:
                continue
            if isinstance(src, str) and (src.startswith(('/DATA/', '/media/')) or _im_example_host_path(src)):
                mounts.append({'service': svcname, 'index': idx, 'source': src, 'target': dest,
                               'file': _im_file_mount_expected(src, dest),
                               'placeholder': _im_example_host_path(src)})
    return mounts[:100]


def _update_env(doc: dict, svcname: str, key: str, value: str) -> None:
    env = doc['services'][svcname].get('environment') or {}
    if isinstance(env, dict):
        if key not in env: raise HTTPException(404, 'Umgebungsvariable nicht vorhanden.')
        previous = str(env[key] or '')
        env[key] = value
    elif isinstance(env, list):
        matches = [i for i, x in enumerate(env) if isinstance(x, str) and x.startswith(key + '=')]
        if len(matches) != 1: raise HTTPException(404, 'Umgebungsvariable nicht eindeutig.')
        i = matches[0]
        previous = env[i].split('=', 1)[1]
        env[i] = f'{key}={value}'
    else:
        raise HTTPException(400, 'Ungültiges environment.')

    # Connection URLs of the same Compose project must use the revised DB
    # username/password too. Only update parsed Postgres URIs matching the old
    # credential, never text-replace a common word like "silo" across YAML.
    if key.upper() in ('POSTGRES_PASSWORD', 'POSTGRES_USER') and previous:
        for service in doc['services'].values():
            e = service.get('environment') or {}
            if isinstance(e, dict):
                entries = [(k, v) for k, v in e.items() if isinstance(v, str)]
            elif isinstance(e, list):
                entries = [(i, x.split('=', 1)[1]) for i, x in enumerate(e) if isinstance(x, str) and '=' in x]
            else:
                continue
            for k, v in entries:
                if not v.startswith(('postgres://', 'postgresql://')): continue
                try:
                    url = urllib.parse.urlsplit(v)
                    if (key.upper() == 'POSTGRES_PASSWORD' and urllib.parse.unquote(url.password or '') != previous
                            or key.upper() == 'POSTGRES_USER' and urllib.parse.unquote(url.username or '') != previous):
                        continue
                    user = value if key.upper() == 'POSTGRES_USER' else urllib.parse.unquote(url.username or '')
                    passwd = value if key.upper() == 'POSTGRES_PASSWORD' else urllib.parse.unquote(url.password or '')
                    newloc = f'{urllib.parse.quote(user, safe="")}:{urllib.parse.quote(passwd, safe="")}@{url.hostname}'
                    if url.port: newloc += f':{url.port}'
                    updated = urllib.parse.urlunsplit(url._replace(netloc=newloc))
                    if isinstance(e, dict): e[k] = updated
                    else: e[k] = f'{e[k].split("=", 1)[0]}={updated}'
                except (ValueError, TypeError):
                    continue


@app.post('/api/nas/folders')
def nas_folders(req: Request, body: BrowseFolders):
    require_write(req)
    if not body.path:
        return {'path': '', 'folders': [{'name': root.lstrip('/'), 'path': root}
                for root in _BROWSE_ROOTS if (_BROWSE_MOUNT / root.lstrip('/')).is_dir()],
                'selectable': False}
    base = _browse_path(body.path)
    try:
        entries = []
        with os.scandir(base) as scan:
            for item in scan:
                if len(entries) >= 500: break
                try:
                    if (not item.is_symlink() and item.is_dir(follow_symlinks=False)
                            and not any(ord(c) < 32 or ord(c) == 127 for c in item.name)
                            and ':' not in item.name and '\\' not in item.name):
                        entries.append({'name': item.name, 'path': body.path.rstrip('/') + '/' + item.name})
                except OSError:
                    continue
    except PermissionError as exc:
        raise HTTPException(403, 'Keine Leseberechtigung für diesen Ordner.') from exc
    entries.sort(key=lambda item: item['name'].casefold())
    return {'path': body.path, 'folders': entries, 'selectable': True, 'truncated': len(entries) >= 500}


@app.post('/api/compose/settings')
def compose_settings(req: Request, body: Source):
    require_write(req)
    doc = safe_yaml(body.value)
    return {'credentials': _credential_fields(doc), 'mounts': _mount_fields(doc),
            'network_ports': _im_network_bindings(doc),
            'credential_warnings': _im_credential_mismatch_warnings(doc),
            'app_urls': _app_url_values(doc),
            'access_services': [{'name': name, 'user': str(svc.get('user', '')),
                                 'mounts': [{'index': idx, 'source': (item.split(':', 1)[0] if isinstance(item, str) else item.get('source', '')),
                                             'target': (item.split(':', 2)[1] if isinstance(item, str) and ':' in item else item.get('target', '') if isinstance(item, dict) else ''),
                                             'read_only': ('ro' in item.split(':', 2)[2].split(',') if isinstance(item, str) and item.count(':') >= 2 else bool(item.get('read_only', False)) if isinstance(item, dict) else False)}
                                            for idx, item in enumerate(svc.get('volumes') or [])
                                            if (isinstance(item, str) and item.startswith('/') and ':' in item) or (isinstance(item, dict) and item.get('type') == 'bind' and str(item.get('source', '')).startswith('/'))]}
                                for name, svc in doc['services'].items()]}


@app.post('/api/compose/app-url')
def compose_app_url(req: Request, body: ComposeAppUrl):
    require_write(req)
    doc = safe_yaml(body.source)
    service = doc['services'].get(body.service)
    if service is None or body.key.upper() not in _APP_URL_KEYS:
        raise HTTPException(404, 'App-Adresse oder Docker-Dienst nicht vorhanden.')
    env = service.get('environment') or {}
    existing = (body.key in env if isinstance(env, dict)
                else any(isinstance(v, str) and v.startswith(body.key + '=') for v in env)
                if isinstance(env, list) else False)
    if not existing:
        raise HTTPException(404, 'URL-Variable nicht vorhanden.')
    if _app_url_invalid(body.value.strip()):
        raise HTTPException(400, 'Bitte die tatsächliche vollständige App-Adresse angeben, z. B. http://NAS-IP:PORT oder https://app.example.de.')
    _update_env(doc, body.service, body.key, body.value.strip())
    return {'source': yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)}


@app.post('/api/compose/access')
def compose_access(req: Request, body: ComposeAccess):
    """Edit one service's Compose user or a single bind-mount access mode.

    Automatic preserves the publisher's original user setting, not an
    invented identity. Callers may explicitly reset to the image default
    by editing the Compose YAML. This avoids privilege escalation.
    """
    require_write(req)
    doc = safe_yaml(body.source)
    service = doc['services'].get(body.service)
    if service is None:
        raise HTTPException(404, 'Docker-Dienst nicht vorhanden.')
    if body.mode == 'mount':
        mounts = service.get('volumes') or []
        if not isinstance(mounts, list) or body.index >= len(mounts) or body.index < 0:
            raise HTTPException(404, 'Volume nicht gefunden.')
        item = mounts[body.index]
        if isinstance(item, str):
            # An explicit host bind is required. Do not modify named volumes.
            parts = item.split(':')
            if len(parts) < 2 or not parts[0].startswith('/') or not parts[1].startswith('/') or len(parts) > 3:
                raise HTTPException(400, 'Nur absolute Host-Bind-Mounts unterstützt.')
            if len(parts) == 3:
                options = [opt for opt in parts[2].split(',') if opt and opt not in ('ro','rw')]
            else:
                options = []
            options.insert(0, 'ro' if body.read_only else 'rw')
            mounts[body.index] = ':'.join((parts[0], parts[1], ','.join(options)))
        elif isinstance(item, dict) and item.get('type') == 'bind' and isinstance(item.get('source'), str) and item['source'].startswith('/'):
            item['read_only'] = body.read_only
        else:
            raise HTTPException(400, 'Dieses Volume ist kein Host-Bind-Mount.')
    elif body.mode == 'automatic':
        # Removing user is an explicit user choice: run as the image default.
        service.pop('user', None)
    elif body.mode == 'root':
        service['user'] = '0:0'
    elif body.mode == 'normal':
        service['user'] = '1000:1000'
    else:
        service['user'] = f'{body.uid}:{body.gid}'
    return {'source': yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)}


# Per-port settings remain user-controlled. The automatic source-import default
# changes only the main Web UI; manual loopback choices remain authoritative.
class ComposeNetwork(BaseModel):
    source: str = Field(min_length=1, max_length=524288)
    service: str = Field(min_length=1, max_length=70)
    index: int = Field(ge=0, le=100)
    exposure: str = Field(pattern=r'^(loopback|lan)$')


def _im_network_bindings(doc: dict) -> list[dict]:
    found = []
    for service_name, service in doc['services'].items():
        for idx, item in enumerate(service.get('ports') or []):
            host_ip, published = None, None
            if isinstance(item, str):
                spec = item.rsplit('/', 1)[0] if item.endswith(('/tcp', '/udp', '/sctp')) else item
                fields = spec.rsplit(':', 2)
                if len(fields) == 3 and re.fullmatch(r'[0-9.]+', fields[0]):
                    host_ip, published = fields[0], fields[1]
                elif len(fields) == 2:
                    published = fields[0]
            elif isinstance(item, dict):
                host_ip = str(item.get('host_ip') or '')
                published = item.get('published')
            if published is None or not str(published).isdigit() or not (1 <= int(published) <= 65535):
                continue
            if host_ip not in ('', None, '127.0.0.1', '0.0.0.0'):
                continue  # Other explicitly configured interfaces unchanged.
            found.append({'service': service_name, 'index': idx,
                          'host_port': int(published),
                          'exposure': 'loopback' if host_ip == '127.0.0.1' else 'lan'})
    return found[:100]


@app.post('/api/compose/network')
def compose_network(req: Request, body: ComposeNetwork):
    require_write(req)
    doc = safe_yaml(body.source)
    service = doc['services'].get(body.service)
    if service is None:
        raise HTTPException(404, 'Dienst nicht vorhanden.')
    ports = service.get('ports') or []
    if not isinstance(ports, list) or body.index >= len(ports):
        raise HTTPException(404, 'Host-Port nicht gefunden.')
    choice = next((v for v in _im_network_bindings(doc)
                   if v['service'] == body.service and v['index'] == body.index), None)
    if choice is None:
        raise HTTPException(400, 'Nur feste TCP/UDP-Ports mit Standard- oder Loopback-IP unterstützt.')
    entry = ports[body.index]
    new_ip = '127.0.0.1' if body.exposure == 'loopback' else '0.0.0.0'
    if isinstance(entry, dict):
        entry['host_ip'] = new_ip
    elif isinstance(entry, str):
        protocol = ''
        core = entry
        if entry.endswith(('/tcp', '/udp', '/sctp')):
            core, slash, p = entry.rpartition('/')
            protocol = slash + p
        parts = core.rsplit(':', 2)
        if len(parts) == 3 and parts[0] in ('127.0.0.1', '0.0.0.0'):
            parts[0] = new_ip
            core = ':'.join(parts)
        elif len(parts) == 2:
            core = f'{new_ip}:{core}'
        else:
            raise HTTPException(400, 'Unbekannte Host-Port-Darstellung.')
        ports[body.index] = core + protocol
    return {'source': yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)}


@app.post('/api/compose/modify')
def compose_modify(req: Request, body: ComposeEdit):
    require_write(req)
    doc = safe_yaml(body.source)
    if body.service not in doc['services']:
        raise HTTPException(404, 'Dienst existiert nicht mehr.')
    service = doc['services'][body.service]
    if body.action == 'environment':
        if not _CREDENTIAL_KEY.search(body.key):
            raise HTTPException(400, 'Dieses Feld darf hier nicht bearbeitet werden.')
        if body.generate:
            if re.search(r'(?:^|_)(?:API|ACCESS|OAUTH|OIDC|CLOUDFLARE|TUNNEL|TS)_?(?:TOKEN|KEY|SECRET)$', body.key.upper()):
                raise HTTPException(400, 'Externe API-Zugangsdaten werden vom Anbieter ausgegeben und nicht lokal erzeugt.')
            if not _CREDENTIAL_KEY.search(body.key):
                raise HTTPException(400, 'Nur lokale Benutzer, Passwörter und Secrets können generiert werden.')
            value = (_im_generate_local_secret(body.key, doc, length=body.length or None,
                                              lowercase=body.lowercase, uppercase=body.uppercase,
                                              digits=body.digits, symbols=body.symbols)
                     if _SECRET_KEY.search(body.key) else 'user_' + secrets.token_hex(5))
        else:
            value = body.value.strip()
            if (not value or any(ord(c) < 32 for c in value)
                    or len(value) > 256 or ':' in value and not _SECRET_KEY.search(body.key)):
                raise HTTPException(400, 'Ungültiger Wert für Benutzername oder Passwort.')
        targets = {(recipient, body.key) for recipient in _im_shared_credential_services(doc, body.service, body.key)}
        targets.update(_im_wordpress_shared_recipient_keys(doc, body.service, body.key))
        for recipient, field in targets:
            _update_env(doc, recipient, field, value)
    else:
        volumes = service.get('volumes') or []
        if body.index < 0 or body.index >= len(volumes):
            raise HTTPException(404, 'Volume nicht vorhanden.')
        item = volumes[body.index]
        before = item.split(':', 1)[0] if isinstance(item, str) else item.get('source') if isinstance(item, dict) else None
        if not isinstance(before, str) or not (before.startswith(('/DATA/', '/media/')) or _im_example_host_path(before)):
            raise HTTPException(400, 'Nur freigegebene NAS-Bind-Mounts und eindeutige Hersteller-Platzhalter sind bearbeitbar.')
        chosen = body.value.strip()
        if (not chosen.startswith(('/DATA/', '/media/')) or len(chosen) > 500
                or ':' in chosen or chr(92) in chosen or any(ord(c) < 32 or ord(c) == 127 for c in chosen)
                or any(part in ('', '.', '..') for part in chosen.split('/')[1:])):
            raise HTTPException(400, 'NAS-Pfad muss absolut unter /DATA/ oder /media/ liegen; keine Platzhalter oder .. verwenden.')
        target = item.split(':', 2)[1] if isinstance(item, str) else str(item.get('target') or '')
        is_file = _im_file_mount_expected(before, target)
        if is_file:
            if not _im_file_mount_expected(chosen, target):
                raise HTTPException(400, 'Der Mount erwartet eine Datei, kein Verzeichnis.')
            # If NAS browse is mounted, refuse nonexistent or symlinked config files.
            root = next((r for r in _BROWSE_ROOTS if chosen.startswith(r + '/')), None)
            physical_root = _BROWSE_MOUNT / str(root or '').lstrip('/')
            if root and physical_root.is_dir():
                f = _BROWSE_MOUNT / chosen.lstrip('/')
                if not f.is_file() or f.is_symlink():
                    raise HTTPException(404, 'Konfigurationsdatei nicht vorhanden oder ungültiger Link. Datei zuerst auf dem NAS anlegen.')
        elif not (chosen.startswith('/DATA/AppData/') and not _im_example_host_path(chosen)):
            _browse_path(chosen)  # Other folder paths must exist and be browsable.
        if isinstance(item, str):
            volumes[body.index] = body.value + item[len(before):]
        else:
            item['source'] = body.value
    return {'source': yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)}


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower().strip()).strip("-")
    value = value[:44].strip("-")
    if not SLUG.fullmatch(value):
        raise HTTPException(400, "App-Name muss aus 3–44 Kleinbuchstaben, Zahlen oder Bindestrichen bestehen.")
    return value


def safe_yaml(source: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        raise HTTPException(400, f"Ungültige YAML-Datei: {str(exc)[:180]}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("services"), dict) or not data["services"]:
        raise HTTPException(400, "Docker Compose benötigt einen nicht leeren 'services'-Block.")
    if len(data["services"]) > 20:
        raise HTTPException(400, "Maximal 20 Dienste pro Installation in der Startversion.")
    for name, service in data["services"].items():
        if not isinstance(service, dict) or not isinstance(name, str) or not re.fullmatch(r"[\w-]{1,70}", name):
            raise HTTPException(400, f"Ungültiger Dienst: {name}")
        if "image" not in service and "build" not in service:
            raise HTTPException(400, f"Dienst '{name}' hat weder Docker-Image noch Build-Kontext.")
        if "image" in service and (not isinstance(service["image"], str) or not IMAGE.fullmatch(service["image"])):
            raise HTTPException(400, f"Ungültiges Image bei '{name}'.")
    return data


# Reverse-proxy installations are opt-in: never accept arbitrary public hosts.
# Comma-separated exact hostnames, e.g. IM_ALLOWED_PROXY_HOSTS=im.example.org.
_PROXY_HOSTS_ENV = {h.strip().lower() for h in os.getenv('IM_ALLOWED_PROXY_HOSTS', '').split(',') if h.strip()}
_PROXY_HOSTS_FILE = Path(os.getenv('IM_PROXY_HOSTS_FILE', '/app/data/install-monitor-proxy-hosts.json'))
_PROXY_HOSTS_LOCK = threading.RLock()
_PROXY_NAME = re.compile(r'^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$', re.I)

def _proxy_hosts() -> set[str]:
    with _PROXY_HOSTS_LOCK:
        try:
            saved = json.loads(_PROXY_HOSTS_FILE.read_text('utf-8'))
            names = saved.get('hosts', [])
            if not isinstance(names, list):
                names = []
        except (OSError, ValueError, AttributeError):
            names = []
        return _PROXY_HOSTS_ENV | {name.lower() for name in names if isinstance(name, str) and _PROXY_NAME.fullmatch(name)}

class ProxyHostChange(BaseModel):
    host: str = Field(min_length=4, max_length=253)
    totp_code: str = Field(pattern=r'^[0-9]{6}$')


def _change_proxy_host(req: Request, body: ProxyHostChange, remove: bool) -> dict:
    require_write(req)
    secret = _totp_saved()
    if not secret:
        raise HTTPException(403, 'Authenticator zuerst einrichten.')
    name = body.host.strip().lower()
    if not _PROXY_NAME.fullmatch(name) or name.endswith(('.local', '.localhost', '.internal', '.test', '.invalid')):
        raise HTTPException(400, 'Öffentlichen DNS-Hostnamen ohne Protokoll, Pfad oder Port angeben.')
    if not _verify_totp(secret, body.totp_code, 'proxy-change:'+str(req.session.get('csrf',''))):
        raise HTTPException(403, 'Authenticator-Code ungültig.')
    with _PROXY_HOSTS_LOCK:
        try:
            obj = json.loads(_PROXY_HOSTS_FILE.read_text('utf-8'))
            hosts = set(obj.get('hosts', [])) if isinstance(obj.get('hosts'), list) else set()
        except (OSError, ValueError, AttributeError):
            hosts = set()
        hosts = {h for h in hosts if isinstance(h, str) and _PROXY_NAME.fullmatch(h)}
        if remove:
            if name in _PROXY_HOSTS_ENV:
                raise HTTPException(409, 'Host stammt aus IM_ALLOWED_PROXY_HOSTS und muss dort entfernt werden.')
            hosts.discard(name)
        else:
            if len(hosts) >= 12 and name not in hosts:
                raise HTTPException(400, 'Maximal 12 zusätzliche Reverse-Proxy-Hosts.')
            hosts.add(name)
        _PROXY_HOSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        import tempfile as _tempfile
        fd, tmp = _tempfile.mkstemp(prefix='.proxy-', dir=str(_PROXY_HOSTS_FILE.parent))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'hosts': sorted(hosts)}, stream)
            os.replace(tmp, _PROXY_HOSTS_FILE)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    return {'proxy_hosts': sorted(_proxy_hosts())}

@app.post('/api/proxy/hosts/add')
def proxy_host_add(req: Request, body: ProxyHostChange):
    return _change_proxy_host(req, body, False)

@app.post('/api/proxy/hosts/remove')
def proxy_host_remove(req: Request, body: ProxyHostChange):
    return _change_proxy_host(req, body, True)

_TOTP_FILE = Path(os.getenv('IM_TOTP_FILE', '/app/data/install-monitor-totp.json'))
_TOTP_PENDING: dict[str, tuple[str, float]] = {}
_TOTP_LAST: dict[str, int] = {}
_TOTP_ATTEMPTS: dict[str, tuple[int, float]] = {}
_TOTP_LOCK = threading.Lock()


def _totp_saved() -> str:
    try:
        obj = json.loads(_TOTP_FILE.read_text(encoding='utf-8'))
        return obj['secret'] if isinstance(obj.get('secret'), str) else ''
    except (OSError, ValueError, KeyError):
        return ''


def _totp_step(secret: str, timestamp: int) -> str:
    key = base64.b32decode(secret.upper() + '=' * ((-len(secret)) % 8), casefold=True)
    digest = hmac.new(key, struct.pack('>Q', timestamp // 30), hashlib.sha1).digest()
    offset = digest[-1] & 15
    number = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff
    return f'{number % 1000000:06d}'


def _verify_totp(secret: str, code: str, replay_id: str, consume: bool = True) -> bool:
    if not re.fullmatch(r'[0-9]{6}', code):
        return False
    now = int(time.time())
    with _TOTP_LOCK:
        attempts, started = _TOTP_ATTEMPTS.get(replay_id, (0, time.monotonic()))
        if time.monotonic() - started > 300:
            attempts, started = 0, time.monotonic()
        if attempts >= 8:
            raise HTTPException(429, 'Zu viele Authenticator-Versuche. In fünf Minuten erneut versuchen.')
        _TOTP_ATTEMPTS[replay_id] = (attempts + 1, started)
        last = _TOTP_LAST.get(replay_id, -1)
        for shift in (-1, 0, 1):
            slot = (now // 30) + shift
            if slot <= last and consume:
                continue
            if hmac.compare_digest(_totp_step(secret, slot * 30), code):
                if consume:
                    _TOTP_LAST[replay_id] = slot
                    _TOTP_ATTEMPTS.pop(replay_id, None)
                return True
    return False


class TotpConfirm(BaseModel):
    code: str = Field(pattern=r'^[0-9]{6}$')


@app.get('/api/totp/status')
def totp_status(req: Request):
    require_auth(req)
    return {'enabled': bool(_totp_saved()), 'proxy_hosts': sorted(_proxy_hosts()), 'requires_install_totp': bool(_totp_saved()) or bool(_proxy_hosts())}


@app.post('/api/totp/setup')
def totp_setup(req: Request):
    require_write(req)
    if _totp_saved():
        raise HTTPException(409, 'Authenticator ist bereits eingerichtet.')
    secret = base64.b32encode(secrets.token_bytes(20)).decode('ascii').rstrip('=')
    with _TOTP_LOCK:
        _TOTP_PENDING[str(req.session['csrf'])] = (secret, time.monotonic() + 300)
    uri = 'otpauth://totp/' + urllib.parse.quote('Install Monitor', safe='') + '?secret=' + secret + '&issuer=Install%20Monitor&digits=6&period=30'
    return {'secret': secret, 'uri': uri, 'expires_seconds': 300}


@app.post('/api/totp/confirm')
def totp_confirm(req: Request, payload: TotpConfirm):
    require_write(req)
    if _totp_saved():
        raise HTTPException(409, 'Authenticator ist bereits eingerichtet.')
    key = str(req.session['csrf'])
    with _TOTP_LOCK:
        pending = _TOTP_PENDING.get(key)
    if not pending or time.monotonic() > pending[1]:
        raise HTTPException(400, 'Einrichtung abgelaufen. Erneut beginnen.')
    if not _verify_totp(pending[0], payload.code, 'setup:'+key):
        raise HTTPException(400, 'Authenticator-Code ungültig.')
    _TOTP_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(_TOTP_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        json.dump({'secret': pending[0]}, out)
    with _TOTP_LOCK:
        _TOTP_PENDING.pop(key, None)
    return {'enabled': True}


def _normalized_zima_host(value: str) -> str:
    """Prefer HTTPS for explicitly approved proxy hostnames, including bare domains."""
    raw = value.strip()
    if '://' in raw:
        return raw
    candidate = urllib.parse.urlsplit('http://' + raw)
    hostname = (candidate.hostname or '').lower()
    if hostname in _proxy_hosts():
        # A nonstandard explicit port is not silently converted to 443.
        return 'https://' + raw
    return 'http://' + raw


def _proxy_guard(req: Request, payload: Install) -> None:
    """Validate allowed public ZimaOS URLs; TOTP is checked separately for every install."""
    host = urllib.parse.urlsplit(_normalized_zima_host(payload.host))
    if host.hostname and host.hostname.lower() in _proxy_hosts():
        if host.scheme != 'https' or host.port not in (None, 443):
            raise HTTPException(400, 'Reverse Proxy erfordert HTTPS auf Port 443. Bitte https:// voranstellen oder nur den freigegebenen Hostnamen eingeben.')



def _internal_zimaos_target(entered_host: str = "") -> str:
    """Resolve an explicit LAN endpoint, or the optional administrator default.

    The public proxy is authentication-only and must NEVER be used as the NAS
    API target. All internal destinations are validated by safe_host against
    loopback, LAN and Tailscale address ranges (including resolved DNS).
    """
    configured = str(entered_host or "").strip() or os.getenv('IM_INTERNAL_ZIMAOS_URL', '').strip()
    if not configured:
        raise HTTPException(
            400,
            'Bitte die interne ZimaOS-Adresse eintragen (z. B. http://NAS-LAN-IP). '
            'Die Install-Monitor-Reverse-Proxy-Domain ist nicht die ZimaOS-Adresse.'
        )
    parsed = urllib.parse.urlsplit(_normalized_zima_host(configured))
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise HTTPException(400, 'Interne ZimaOS-Adresse muss eine gültige LAN-IP oder ein lokaler Hostname sein.')
    if parsed.hostname.lower() in _proxy_hosts():
        raise HTTPException(400, 'Als interne ZimaOS-Adresse eine LAN-IP statt der Reverse-Proxy-Domain eingeben.')
    # Explicit internal hosts and environment-provided defaults use the same
    # private-destination validation; never follow a public DNS target.
    return safe_host(configured)


def _install_target(req: Request, payload: Install) -> Install:
    """Enforce TOTP on installs once configured or when proxy access is enabled.

    A reverse proxy may rewrite Host or X-Forwarded-* headers. Therefore the
    factor cannot depend on the submitted ZimaOS address or guessed request
    origin: doing so permits bypass by entering the NAS LAN IP.
    """
    if _totp_saved() or _proxy_hosts():
        secret = _totp_saved()
        if not secret:
            raise HTTPException(403, 'Reverse Proxy ist freigegeben. Authenticator zuerst in den Install-Monitor-Einstellungen einrichten.')
        if not _verify_totp(secret, payload.totp_code, 'install:'+str(req.session.get('csrf',''))):
            raise HTTPException(403, 'Authenticator-Code fehlt oder ist ungültig.')
    submitted = urllib.parse.urlsplit(_normalized_zima_host(payload.host))
    if submitted.hostname and submitted.hostname.lower() in _proxy_hosts():
        _proxy_guard(req, payload)
        local_target = _internal_zimaos_target(payload.internal_host)
        return payload.model_copy(update={'host': local_target})
    # Never silently map non-allowlisted external destinations to the NAS.
    return payload.model_copy(update={'host': safe_host(payload.host)})


def _check_target(host: str, internal_host: str = "") -> str:
    """Read-only verification uses the same validated private API destination."""
    submitted = urllib.parse.urlsplit(_normalized_zima_host(host))
    if submitted.hostname and submitted.hostname.lower() in _proxy_hosts():
        return _internal_zimaos_target(internal_host)
    return safe_host(host)


def safe_host(host: str) -> str:
    parsed = urllib.parse.urlsplit(_normalized_zima_host(host))
    if parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise HTTPException(400, "ZimaOS-Host nur als IP oder Hostname, ohne Pfad, eingeben.")
    if parsed.scheme not in ("http", "https") or not parsed.hostname or not re.fullmatch(r"[a-zA-Z0-9.:-]{1,253}", parsed.hostname):
        raise HTTPException(400, "Ungültige ZimaOS-Adresse.")
    proxy = parsed.hostname.lower() in _proxy_hosts()
    if proxy and (parsed.scheme != 'https' or parsed.port not in (None, 443)):
        raise HTTPException(400, 'Reverse Proxy nur mit HTTPS auf Port 443 erlaubt.')
    # Public destinations are permitted only when explicitly allowlisted.
    local_nets = [ipaddress.ip_network(network) for network in (
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "127.0.0.0/8", "100.64.0.0/10", "fc00::/7", "::1/128")]
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        if not addresses or (not proxy and any(not any(ipaddress.ip_address(a[4][0]) in subnet for subnet in local_nets) for a in addresses)):
            raise HTTPException(400, "ZimaOS muss über LAN, Loopback oder Tailscale erreichbar sein.")
    except socket.gaierror as exc:
        raise HTTPException(400, "ZimaOS-Hostname kann nicht aufgelöst werden.") from exc
    return f"{parsed.scheme}://{parsed.netloc}"


# Persist only the ZimaOS endpoint. Credentials and TOTP codes remain
# per-request and are never written to disk by this configuration feature.
_ZIMAOS_TARGET_FILE = Path(os.getenv('IM_ZIMAOS_TARGET_FILE', '/app/data/install-monitor-zimaos-target.json'))
_ZIMAOS_TARGET_LOCK = threading.RLock()


class ZimaOsTargetSave(BaseModel):
    host: str = Field(min_length=1, max_length=256)


def _saved_zimaos_host() -> str:
    with _ZIMAOS_TARGET_LOCK:
        try:
            saved = json.loads(_ZIMAOS_TARGET_FILE.read_text('utf-8'))
            value = saved.get('host', '') if isinstance(saved, dict) else ''
            if isinstance(value, str) and 0 < len(value) <= 256:
                return value
        except (OSError, ValueError):
            pass
    return os.getenv('IM_INTERNAL_ZIMAOS_URL', '').strip()


@app.get('/api/zimaos/target')
def get_zimaos_target(req: Request):
    require_auth(req)
    return {'host': _saved_zimaos_host()}


@app.post('/api/zimaos/target')
def save_zimaos_target(req: Request, body: ZimaOsTargetSave):
    require_write(req)
    host = safe_host(body.host.strip())
    with _ZIMAOS_TARGET_LOCK:
        _ZIMAOS_TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.zimaos-target-', dir=str(_ZIMAOS_TARGET_FILE.parent))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'host': host}, stream)
            os.replace(name, _ZIMAOS_TARGET_FILE)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return {'host': host}


def _public_remote(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or p.username or p.password or not p.hostname:
        raise HTTPException(400, "Nur öffentliche HTTPS-Links sind erlaubt.")
    if p.port not in (None, 443):
        raise HTTPException(400, "Quell-URLs dürfen keinen anderen Port verwenden.")
    # limit remote YAML sources to known code hosts; no SSRF against the NAS or LAN.
    allowed = {"github.com", "raw.githubusercontent.com", "api.github.com", "gitlab.com", "codeberg.org", "raw.codeberg.page", "gist.githubusercontent.com", "gitea.baerentsen.space", "hub.docker.com"}
    if p.hostname.lower() not in allowed:
        raise HTTPException(400, "Quelle nicht freigegeben. Bitte den YAML-Inhalt direkt einfügen.")
    try:
        addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise HTTPException(400, "Quelle verweist auf eine interne Adresse.")
    except socket.gaierror as exc:
        raise HTTPException(400, "Quellserver kann nicht aufgelöst werden.") from exc
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward NAS credentials or ZimaOS session JWT through a redirect.
        return None


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _public_remote(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        # Prevent cross-host credential forwarding, including to github.com
        # or raw.githubusercontent.com. Only api.github.com receives a PAT.
        if redirected is not None and urllib.parse.urlsplit(newurl).hostname != 'api.github.com':
            redirected.remove_header('Authorization')
            redirected.unredirected_hdrs.pop('Authorization', None)
        return redirected


# Compose substitutions are performed only on downloaded repository YAML.
# Values always appear in the editable source editor before installation.
COMPOSE_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:-|-)([^}]*))?\}")
GITHUB_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def _download_remote(url: str, max_bytes: int = 524288) -> str:
    url = _public_remote(url)
    try:
        opener = urllib.request.build_opener(SafeRedirect())
        headers = {"User-Agent": "InstallMonitor/0.2.7", "Accept": "application/vnd.github+json, application/yaml, text/plain, */*"}
        if urllib.parse.urlsplit(url).hostname == 'api.github.com':
            token = _gh_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
                headers['X-GitHub-Api-Version'] = '2022-11-28'
        req = urllib.request.Request(url, headers=headers)
        with opener.open(req, timeout=12) as res:
            content_type = res.headers.get("Content-Type", "").lower()
            data = res.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(400, "Quell-Datei ist zu groß. Bitte eine kleinere Compose-Datei auswählen.")
        text = data.decode("utf-8-sig")
        if "text/html" in content_type or re.match(r"\s*(?:<!doctype\s+html|<html[\s>])", text, re.I):
            raise HTTPException(400, "Das ist eine Webseite statt einer Compose-YAML-Datei. Bitte einen Dateilink verwenden.")
        return text
    except urllib.error.HTTPError as exc:
        is_github_api = urllib.parse.urlsplit(url).hostname == 'api.github.com'
        if is_github_api and exc.code == 401:
            message = 'GitHub-API-Token abgelehnt (HTTP 401). Token in Einstellungen prüfen.'
        elif is_github_api and exc.code in (403, 429) and (exc.headers.get('X-RateLimit-Remaining') == '0' or exc.code == 429):
            message = 'GitHub-API-Limit erreicht. API-Nutzungslimit in Einstellungen prüfen.'
        elif is_github_api and exc.code == 403:
            message = 'GitHub-API-Zugriff nicht erlaubt (HTTP 403). Token-Berechtigungen prüfen.'
        else:
            message = f'Quelle nicht erreichbar (HTTP {exc.code}).' 
        raise HTTPException(400, message) from exc
    except (urllib.error.URLError, UnicodeDecodeError, TimeoutError) as exc:
        raise HTTPException(400, f"Datei konnte nicht abgerufen werden: {str(exc)[:150]}") from exc


def _github_json(url: str) -> dict:
    try:
        doc = json.loads(_download_remote(url, max_bytes=2500000))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(400, "GitHub lieferte keine gültigen Repository-Informationen.") from exc
    if not isinstance(doc, dict):
        raise HTTPException(400, "GitHub lieferte ein unerwartetes Ergebnis.")
    return doc


def _compose_score(path: str) -> int:
    lower = path.lower()
    file = lower.rsplit("/", 1)[-1]
    if not (file.endswith(".yaml") or file.endswith(".yml")):
        return -1
    # A publisher may ship a native ZimaOS app under an application-specific
    # name, e.g. zimapp-zimaos.yml. It is still a Compose file with x-casaos
    # metadata. Do not accept arbitrary *.yml files or blueprint examples.
    zimaos_package = bool(re.search(r"(?:^|[-_.])zimaos(?:[-_.]|$)", file))
    if not ("compose" in file or file in ("stack.yml", "stack.yaml") or zimaos_package):
        return -1
    # Never auto-install developer containers, CI/test stacks, or example
    # dependencies. The publisher's official production recipe must be selected
    # instead; direct user-supplied Compose URLs remain untouched.
    path_parts = lower.split('/')
    if any(p in _GITHUB_SKIP_PARTS for p in path_parts[:-1]):
        return -1
    if re.search(r"(?:^|[/\.\-_])(dev|test|tests|testing|ci|e2e|unit|integration|localdev|playwright|cypress)(?:[/\.\-_]|$)", lower):
        return -1
    score = 30
    if re.search(r"(?:^|[-_.])zimaos(?:[-_.]|$)", file):
        score += 185  # A specifically supplied ZimaOS template outranks the generic variant.
    if file in ("compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"):
        score += 90
    if any(folder in ('_docker', '.docker', 'docker', 'compose', 'deploy') for folder in lower.split('/')[:-1]):
        score += 18
    if "prod" in file or "production" in file:
        score += 35
    if "pg18" in file:
        score += 12
    if "supervised" in lower or "unraid" in lower:
        score -= 45
    if any(folder in _GITHUB_EXAMPLE_DIRS for folder in path_parts[:-1]):
        score -= 48  # Example is a candidate, but less trustworthy than a production Compose.
    elif 'example' in lower:
        score -= 12
    if "override" in file:
        score -= 90
    score -= min(path.count("/") * 4, 40)
    return score


def _github_logo(owner: str, repo: str, branch: str, tree: dict) -> str:
    """Only use an image actually listed in the application's own repository."""
    ranked: list[tuple[int, str]] = []
    for item in tree.get("tree", []):
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        path = item.get("path", "")
        if not isinstance(path, str) or len(path) > 255:
            continue
        low = path.lower()
        filename = low.rsplit("/", 1)[-1]
        if not re.fullmatch(r"(?:icon|logo|app[-_]icon|brand[-_]logo)(?:[-_][a-z0-9]+)?\.(?:png|webp|svg)", filename):
            continue
        if re.search(r"(?:^|/)(?:test|tests|fixture|node_modules|example|examples)(?:/|$)", low):
            continue
        score = 200 - min(path.count("/") * 20, 100)
        if filename == "icon.png": score += 40
        elif filename == "logo.png": score += 30
        elif filename in ("icon.svg", "logo.svg"): score += 25
        if low.startswith(("assets/", "static/", "public/")): score += 10
        if low.startswith(("docs/", "documentation/")): score -= 40
        ranked.append((score, path))
    if not ranked:
        return ""
    path = sorted(ranked, key=lambda x: (-x[0], len(x[1]), x[1]))[0][1]
    return "https://raw.githubusercontent.com/" + "/".join(
        urllib.parse.quote(x, safe="") for x in (owner, repo, branch, *path.split("/")))




# GitHub's root Git tree omits nested assets/ by design. For large projects,
# descend into asset-oriented directories using the Git tree SHA rather than
# downloading the (potentially multi-megabyte) full recursive repository tree.
PROJECT_ICON_EXTENSIONS = {".png", ".svg", ".webp", ".ico", ".jpg", ".jpeg", ".avif"}
PROJECT_ICON_DIRECTORIES = {
    "assets", "images", "img", "icons", "icon", "logos", "logo",
    "branding", "brand", "public", "static", "resources", "res", "web",
    "www", "frontend", "client", "ui", "app", "src", "docs", "documentation", "assets-source",
}
PROJECT_ICON_EXCLUDE = {"node_modules", "vendor", "dist", "build", "test", "tests", "fixtures", "examples", ".git"}


def _icon_candidate(owner: str, repo: str, branch: str, entry: dict, prefix: str = "") -> dict | None:
    if not isinstance(entry, dict) or entry.get("type") != "blob":
        return None
    relative = entry.get("path", "")
    if not isinstance(relative, str):
        return None
    path = (prefix + "/" + relative).strip("/")
    segments = path.split("/")
    if (not path or len(path) > 350 or any(not part or part in (".", "..") for part in segments)
            or any(any(ord(c) < 32 for c in part) for part in segments)):
        return None
    low = path.lower()
    if any(section.lower() in PROJECT_ICON_EXCLUDE for section in segments[:-1]):
        return None
    name = segments[-1].lower()
    dot = name.rfind(".")
    extension = name[dot:] if dot >= 0 else ""
    if extension not in PROJECT_ICON_EXTENSIONS:
        return None
    if isinstance(entry.get("size"), int) and entry["size"] > 2_000_000:
        return None
    if any(x in name for x in ("screenshot", "screen-shot", "banner", "background", "wallpaper", "placeholder", "avatar", "demo", "thumbnail", "spinner")):
        return None
    if not (re.search(r"(?:^|[-_.])(logo|icon|favicon|wordmark|app-icon|app_logo|brandmark|symbol)(?:[-_.]|$)", name)
            or re.search(r"(?:^|[-_.])" + re.escape(repo.lower()) + r"(?:[-_.]|$)", name)):
        return None
    score = 0
    if re.search(r"(?:^|[-_.])icon(?:[-_.]|$)", name): score += 140
    if re.search(r"(?:^|[-_.])logo(?:[-_.]|$)", name): score += 120
    if 'favicon' in name: score += 90
    if 'wordmark' in name: score += 55
    if name.startswith('app-') or name.startswith('app_'): score += 15
    if name.startswith(repo.lower() + '.'): score += 55
    if extension in ('.png', '.svg', '.webp'): score += 25
    if extension == '.ico': score -= 15
    if low.startswith(('assets/', 'public/', 'static/', 'icons/', 'web/public/')): score += 30
    if low.startswith(('docs/', 'documentation/')): score -= 25
    score -= min(path.count('/') * 4, 32)
    url = 'https://raw.githubusercontent.com/' + '/'.join(
        urllib.parse.quote(part, safe='') for part in (owner, repo, branch, *segments))
    return {'path': path, 'url': url, 'format': extension[1:].upper(), 'score': score}


def _project_icon_candidates(project_url: str) -> dict:
    """Bounded, read-only scan of image assets from an exact public GitHub repo.

    A large repository is searched in likely image directories without fetching
    a huge recursive Git tree. No local files or arbitrary remote hosts are read.
    """
    parts = urllib.parse.urlsplit(project_url)
    chunks = parts.path.strip('/').split('/')
    if (parts.scheme != 'https' or parts.hostname != 'github.com' or parts.port is not None
            or parts.username or parts.password or parts.query or parts.fragment
            or len(chunks) != 2 or not all(GITHUB_PART.fullmatch(part) and part not in (".", "..") for part in chunks)):
        raise HTTPException(400, 'Für die Logo-Suche ist ein öffentlicher GitHub-Repository-Link erforderlich.')
    owner, repo = chunks
    metadata = _github_json(f'https://api.github.com/repos/{owner}/{repo}')
    branch = metadata.get('default_branch')
    if not isinstance(branch, str) or not branch or len(branch) > 150:
        raise HTTPException(400, 'Der Standardbranch des GitHub-Projekts wurde nicht gefunden.')
    base = f'https://api.github.com/repos/{owner}/{repo}/git/trees/'
    root = _github_json(base + urllib.parse.quote(branch, safe=''))
    candidates = {}
    def add_entries(tree: dict, prefix: str = '') -> None:
        for entry in tree.get('tree', []):
            item = _icon_candidate(owner, repo, branch, entry, prefix)
            if item is not None:
                old = candidates.get(item['path'])
                if old is None or item['score'] > old['score']:
                    candidates[item['path']] = item

    add_entries(root)
    expanded = 0
    limited = bool(root.get('truncated'))
    # Small repositories can be indexed completely. GitHub sometimes rejects
    # massive recursive replies; fall back to targeted directory exploration.
    if isinstance(metadata.get('size'), int) and metadata['size'] <= 50000:
        try:
            full = _github_json(base + urllib.parse.quote(branch, safe='') + '?recursive=1')
            if not full.get('truncated'):
                add_entries(full)
                items = sorted(candidates.values(), key=lambda x: (-x['score'], x['path']))[:36]
                return {'project_url': f'https://github.com/{owner}/{repo}', 'icons': items, 'limited': False}
            limited = True
        except HTTPException:
            limited = True

    # Breadth-first traversal prioritizes relevant directories. Expand only
    # Git tree objects, never source blobs. At most 18 additional GitHub calls.
    pending = []
    for entry in root.get('tree', []):
        if not isinstance(entry, dict) or entry.get('type') != 'tree':
            continue
        name = str(entry.get('path', '')).lower()
        if name in PROJECT_ICON_DIRECTORIES and isinstance(entry.get('sha'), str):
            pending.append((entry['path'], entry['sha'], 1))
    priority = {'assets':0,'icons':0,'logos':0,'public':1,'static':1,'branding':1,'images':1,'web':2,'frontend':3,'client':3,'app':4,'docs':5,'src':6}
    pending.sort(key=lambda x: (priority.get(x[0].lower(), 4), x[0]))
    visited = set()
    while pending and expanded < 12:
        prefix, sha, depth = pending.pop(0)
        if sha in visited:
            continue
        visited.add(sha)
        expanded += 1
        try:
            subtree = _github_json(base + urllib.parse.quote(sha, safe=''))
        except HTTPException:
            limited = True
            continue
        add_entries(subtree, prefix)
        if depth >= 4:
            continue
        for child in subtree.get('tree', []):
            if not isinstance(child, dict) or child.get('type') != 'tree':
                continue
            name = child.get('path', '')
            if not isinstance(name, str) or name.lower() not in PROJECT_ICON_DIRECTORIES:
                continue
            child_sha = child.get('sha')
            if isinstance(child_sha, str) and len(child_sha) <= 70:
                pending.append((prefix + '/' + name, child_sha, depth + 1))
    limited = limited or bool(pending) or (isinstance(metadata.get('size'), int) and metadata['size'] > 50000)
    items = sorted(candidates.values(), key=lambda x: (-x['score'], x['path']))[:36]
    return {'project_url': f'https://github.com/{owner}/{repo}', 'icons': items, 'limited': limited}


# Public icon catalogs. Source metadata controls format and color availability;
# do not invent variants that have not been declared by the publisher.
_DASHBOARD_INDEX_URL = 'https://raw.githubusercontent.com/homarr-labs/dashboard-icons/main/metadata.json'
_DASHBOARD_ICON_BASE = 'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons'
_SELFHST_INDEX_URL = 'https://raw.githubusercontent.com/selfhst/icons/main/index.json'
_SELFHST_ICON_BASE = 'https://cdn.jsdelivr.net/gh/selfhst/icons'
_SIMPLE_ICONS_INDEX_URL = 'https://raw.githubusercontent.com/simple-icons/simple-icons/develop/data/simple-icons.json'
_SIMPLE_ICONS_BASE = 'https://cdn.simpleicons.org'
# TechIcons.dev attributes its artwork to Devicon. Use the public Devicon
# manifest, not guessed URLs or undocumented TechIcons endpoints.
_TECHICONS_INDEX_URL = 'https://raw.githubusercontent.com/devicons/devicon/master/devicon.json'
_TECHICONS_ICON_BASE = 'https://cdn.jsdelivr.net/gh/devicons/devicon@master/icons'
_DASHBOARD_INDEX_LOCK = threading.Lock()
_DASHBOARD_INDEX_CACHE: dict[str, Any] = {'until': 0.0, 'entries': {}, 'error': ''}
_SELFHST_INDEX_CACHE: dict[str, Any] = {'until': 0.0, 'entries': {}, 'error': ''}
_SIMPLE_ICONS_INDEX_CACHE: dict[str, Any] = {'until': 0.0, 'entries': {}, 'error': ''}
_TECHICONS_INDEX_CACHE: dict[str, Any] = {'until': 0.0, 'entries': {}, 'error': ''}
_ICON_NOISE = frozenset(('app', 'apps', 'server', 'service', 'services', 'main', 'web',
                         'frontend', 'backend', 'latest', 'stable', 'release', 'linuxserver',
                         'official', 'docker', 'dockerfile', 'image', 'container', 'compose',
                         'ghcr', 'library', 'database', 'proxy', 'worker'))
_ICON_SLUG_RE = re.compile(r'[a-z0-9][a-z0-9-]{0,90}\Z')


def _icon_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', str(value).lower()).strip('-')[:90]


def _load_public_catalog(url: str, cache: dict, convert, label: str) -> tuple[dict, str]:
    now = time.monotonic()
    with _DASHBOARD_INDEX_LOCK:
        if cache['until'] > now:
            return cache['entries'], cache['error']
    try:
        request = urllib.request.Request(url, headers={
            'Accept': 'application/json', 'User-Agent': 'InstallMonitor/0.2.13'})
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=7) as response:
            raw = response.read(2_600_001)
        if len(raw) > 2_600_000:
            raise ValueError('Icon-Katalog zu groß')
        parsed = json.loads(raw.decode('utf-8'))
        entries = convert(parsed)
        if not entries:
            raise ValueError('Ungültiger Icon-Katalog')
        error = ''
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as ex:
        with _DASHBOARD_INDEX_LOCK:
            old = cache['entries']
            if old:
                cache['until'] = now + 300
                return old, label + ': zwischengespeicherte Daten verwendet.'
        entries = {}
        error = label + ': derzeit nicht erreichbar (' + type(ex).__name__ + ').'
    with _DASHBOARD_INDEX_LOCK:
        cache.update({'until': now + (21600 if entries else 180),
                      'entries': entries, 'error': error})
    return entries, error


def _dash_index() -> tuple[dict, str]:
    def convert(data):
        if not isinstance(data, dict): return {}
        return {slug: info for slug, info in data.items()
                if isinstance(slug, str) and _ICON_SLUG_RE.fullmatch(slug)
                and isinstance(info, dict) and info.get('base') in ('svg', 'png', 'webp')}
    return _load_public_catalog(_DASHBOARD_INDEX_URL, _DASHBOARD_INDEX_CACHE,
                                convert, 'Dashboard Icons')


def _selfhst_index() -> tuple[dict, str]:
    def convert(data):
        if not isinstance(data, list): return {}
        result = {}
        for row in data[:12000]:
            if not isinstance(row, dict): continue
            slug = row.get('Reference')
            if isinstance(slug, str) and _ICON_SLUG_RE.fullmatch(slug) and any(
                  row.get(k) == 'Yes' for k in ('SVG','PNG','WebP')):
                result[slug] = row
        return result
    return _load_public_catalog(_SELFHST_INDEX_URL, _SELFHST_INDEX_CACHE,
                                convert, 'selfh.st/icons')


def _simple_icon_slug(title: str) -> str:
    # Match Simple Icons SDK titleToSlug() when no explicit slug is supplied.
    swaps = {'+':'plus', '.':'dot', '&':'and', 'đ':'d', 'ħ':'h', 'ı':'i',
             'ĸ':'k', 'ŀ':'l', 'ł':'l', 'ß':'ss', 'ŧ':'t', 'ø':'o'}
    normalized = ''.join(swaps.get(ch, ch) for ch in title.lower())
    normalized = unicodedata.normalize('NFD', normalized)
    return re.sub(r'[^a-z0-9]', '', normalized)


def _simpleicons_index() -> tuple[dict, str]:
    def convert(data):
        if not isinstance(data, list): return {}
        result = {}
        for row in data[:8000]:
            if not isinstance(row, dict) or not isinstance(row.get('title'), str): continue
            slug = row.get('slug') or _simple_icon_slug(row['title'])
            color = row.get('hex')
            if (isinstance(slug, str) and _ICON_SLUG_RE.fullmatch(slug)
                and isinstance(color, str) and re.fullmatch(r'[0-9A-Fa-f]{6}', color)):
                result[slug] = row
        return result
    return _load_public_catalog(_SIMPLE_ICONS_INDEX_URL, _SIMPLE_ICONS_INDEX_CACHE,
                                convert, 'Simple Icons')


def _techicons_index() -> tuple[dict, str]:
    """Devicon metadata, the publicly credited source of TechIcons.dev.

    Only published SVG filenames from versions.svg are exposed. TechIcons
    itself offers PNG downloads, but no supported public PNG URL contract
    was found, so do not invent one.
    """
    def convert(data):
        if not isinstance(data, list): return {}
        entries = {}
        for row in data[:3000]:
            if not isinstance(row, dict): continue
            slug = row.get('name')
            if not isinstance(slug, str) or not _ICON_SLUG_RE.fullmatch(slug): continue
            versions = row.get('versions')
            names = versions.get('svg') if isinstance(versions, dict) else []
            if not isinstance(names, list): continue
            supported = [v for v in names if isinstance(v, str) and _ICON_SLUG_RE.fullmatch(v)]
            if supported: entries[slug] = dict(row, _svg_versions=supported[:12])
        return entries
    return _load_public_catalog(_TECHICONS_INDEX_URL, _TECHICONS_INDEX_CACHE,
                                convert, 'TechIcons / Devicon')


def _icon_variant_urls(base: str, names: dict, formats: tuple[str, ...]) -> list[dict]:
    variants = []
    for theme in ('base', 'light', 'dark'):
        name = names.get(theme)
        if not isinstance(name, str) or not _ICON_SLUG_RE.fullmatch(name):
            continue
        for fmt in formats:
            fmt = fmt.lower()
            if fmt not in ('svg','png','webp'): continue
            variants.append({'theme': theme, 'format': fmt.upper(),
                             'url': f'{base}/{fmt}/{name}.{fmt}'})
    return variants


def _matching_icon_score(slug: str, aliases: list, terms: list[str], query: str) -> int:
    alias_keys = []
    for a in aliases[:25]:
        if isinstance(a, str) and len(a) < 130:
            key = _icon_key(a)
            if key and key not in alias_keys: alias_keys.append(key)
    if query:
        if slug == query: return 1000
        if query in alias_keys: return 970
        if slug.startswith(query): return 620
        if any(a.startswith(query) for a in alias_keys): return 550
        if query in slug: return 330
        if any(query in a for a in alias_keys): return 280
        return 0
    score = 0
    for i, term in enumerate(terms):
        if slug == term: score = max(score, 1000-i*10)
        elif term in alias_keys: score = max(score, 930-i*10)
    return score


def _catalog_matches(terms: list[str], query: str = '', count: int = 24,
                     source: str = 'all') -> tuple[list[dict], str]:
    # Fetch only the selected public catalogue. Each index has its own cache,
    # allowing selfh.st searches even when another provider is unavailable.
    dashboard, dashboard_warning = _dash_index() if source in ('all', 'dashboardicons') else ({}, '')
    external, external_warning = _selfhst_index() if source in ('all', 'selfhst') else ({}, '')
    simple, simple_warning = _simpleicons_index() if source in ('all', 'simpleicons') else ({}, '')
    tech, tech_warning = _techicons_index() if source in ('all', 'techicons') else ({}, '')
    warning = ' '.join(x for x in (dashboard_warning, external_warning, simple_warning, tech_warning) if x)
    clean = []
    for term in terms[:16]:
        if not isinstance(term, str) or len(term) > 120: continue
        key = _icon_key(term)
        if len(key) >= 3 and key not in _ICON_NOISE and key not in clean:
            clean.append(key)
    query_key = _icon_key(query) if query.strip() else ''
    if query_key and len(query_key) < 2: return [], warning
    scored = []
    for slug, entry in dashboard.items():
        if slug in _ICON_NOISE and not query_key: continue
        score = _matching_icon_score(slug, entry.get('aliases') or [], clean, query_key)
        if score: scored.append((score, 0, slug, entry))
    for slug, entry in external.items():
        if slug in _ICON_NOISE and not query_key: continue
        aliases = [entry.get('Name', '')] + [x.strip() for x in str(entry.get('Tags') or '').split(',')]
        score = _matching_icon_score(slug, aliases, clean, query_key)
        # Source catalogue icons should precede external matches of same name.
        if score: scored.append((score, 1, slug, entry))
    for slug, entry in simple.items():
        if slug in _ICON_NOISE and not query_key: continue
        aliases_data = entry.get('aliases') if isinstance(entry.get('aliases'), dict) else {}
        aliases = [entry.get('title', '')] + [x for x in aliases_data.get('aka', []) if isinstance(x,str)]
        score = _matching_icon_score(slug, aliases, clean, query_key)
        if score: scored.append((score, 2, slug, entry))
    for slug, entry in tech.items():
        if slug in _ICON_NOISE and not query_key: continue
        aliases = entry.get('altnames') if isinstance(entry.get('altnames'), list) else []
        score = _matching_icon_score(slug, aliases, clean, query_key)
        if score: scored.append((score, 3, slug, entry))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    results = []
    for score, origin_kind, slug, info in scored[:max(1, min(count, 30))]:
        if origin_kind == 0:
            colors = info.get('colors') if isinstance(info.get('colors'), dict) else {}
            names = {'base':slug}
            for theme in ('light','dark'):
                name = colors.get(theme)
                if isinstance(name, str) and _ICON_SLUG_RE.fullmatch(name): names[theme] = name
            variants = _icon_variant_urls(_DASHBOARD_ICON_BASE, names, ('svg','png','webp'))
            label = 'Dashboard Icons'
            detail = f'https://dashboardicons.com/icons/{slug}'
        elif origin_kind == 1:
            names = {'base':slug}
            for theme in ('light','dark'):
                if info.get(theme.capitalize()) == 'Yes': names[theme] = slug + '-' + theme
            available = tuple(k.lower() for k in ('SVG','PNG','WebP') if info.get(k) == 'Yes')
            variants = _icon_variant_urls(_SELFHST_ICON_BASE, names, available)
            label = 'selfh.st/icons'
            detail = 'https://selfh.st/icons/'
        elif origin_kind == 2:
            color = info['hex'].lower()
            # Simple Icons public colorable CDN exposes SVG, without any invented PNG endpoint.
            variants = [{'theme':'base', 'format':'SVG', 'url':f'{_SIMPLE_ICONS_BASE}/{slug}/{color}'},
                        {'theme':'light', 'format':'SVG', 'url':f'{_SIMPLE_ICONS_BASE}/{slug}/000000'},
                        {'theme':'dark', 'format':'SVG', 'url':f'{_SIMPLE_ICONS_BASE}/{slug}/ffffff'}]
            label = 'Simple Icons'
            detail = f'https://simpleicons.org/?q={slug}'
        else:
            # Devicon versions from its official index. Show distinct SVG
            # variants (original/plain/line/wordmark), no speculative PNGs.
            versions = info.get('_svg_versions', [])
            variants = [{'theme':'base', 'format':'SVG',
                         'label': v.replace('-', ' ').title(),
                         'url':f'{_TECHICONS_ICON_BASE}/{slug}/{slug}-{v}.svg'}
                        for v in versions]
            label = 'TechIcons / Devicon'
            detail = f'https://techicons.dev/icons/{slug}'
        if not variants: continue
        # PNG is a safe default for ZimaOS tiles; user may select SVG or WebP.
        preferred = next((v for v in variants if v['theme']=='base' and v['format']=='PNG'), variants[0])
        results.append({'path':slug, 'url':preferred['url'], 'format':preferred['format'],
                        'score':score, 'origin':('dashboardicons' if origin_kind == 0 else 'selfhst' if origin_kind == 1 else 'simpleicons' if origin_kind == 2 else 'techicons'),
                        'source_label':label, 'variants':variants, 'detail_url':detail})
    return results, warning


def _compose_icon_terms(doc: dict, name: str, typed_image: str = '') -> list[str]:
    """Use only the Compose project and main app image, not unrelated sidecars."""
    terms: list[str] = []
    def add(v):
        if not isinstance(v, str): return
        n = _icon_key(v)
        if n and n not in terms and n not in _ICON_NOISE:
            terms.append(n)
    add(name)
    add(doc.get('name'))
    services = doc.get('services') or {}
    if not isinstance(services, dict): return terms
    infra = ('postgres', 'redis', 'mariadb', 'mysql', 'valkey', 'mongo', 'rabbitmq', 'memcached')
    for service_name, service in list(services.items())[:16]:
        if not isinstance(service, dict): continue
        image = str(service.get('image') or '')
        if any(tag in str(service_name).lower() or tag in image.lower() for tag in infra):
            continue
        add(service_name)
        if image:
            image_path = image.split('@', 1)[0].rsplit(':', 1)[0]  # simple tag
            parts = image_path.split('/')
            add(parts[-1])
            if len(parts) > 1 and parts[-1].lower() in _ICON_NOISE:
                add(parts[-2])
        labels = service.get('labels') or {}
        if isinstance(labels, dict):
            add(labels.get('org.opencontainers.image.title'))
    if typed_image and IMAGE.fullmatch(typed_image):
        add(typed_image.rsplit('/', 1)[-1].split(':', 1)[0])
    return terms[:16]


def _embedded_compose_github(doc: dict) -> str:
    """Trusted only as a search *hint*, never used for arbitrary HTTP fetches."""
    services = doc.get('services') or {}
    for svc in services.values() if isinstance(services, dict) else []:
        if not isinstance(svc, dict): continue
        labels = svc.get('labels') or {}
        if isinstance(labels, list):
            labels = dict(x.split('=', 1) for x in labels if isinstance(x, str) and '=' in x)
        if not isinstance(labels, dict): continue
        raw = labels.get('org.opencontainers.image.source') or labels.get('org.opencontainers.image.url') or ''
        m = re.fullmatch(r'https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/)?', str(raw))
        if m and GITHUB_PART.fullmatch(m.group(1)) and GITHUB_PART.fullmatch(m.group(2)):
            return f'https://github.com/{m.group(1)}/{m.group(2)}'
    return ''


@app.post('/api/icons/search')
def search_icons(req: Request, body: IconCatalogSearch):
    require_write(req)
    # Project logos retain priority; an API or network failure must not break
    # manually searching the public icon catalogue.
    own_icons = []
    limited = False
    if body.source in ('all', 'project') and body.project_url and not body.query.strip():
        try:
            project = _project_icon_candidates(body.project_url)
            own_icons = [dict(x, origin='project', source_label='Originalprojekt')
                         for x in project.get('icons', [])[:12]]
            limited = bool(project.get('limited'))
        except HTTPException:
            limited = True
    catalog, warning = _catalog_matches(body.terms, body.query, source=body.source)
    return {'icons': own_icons + catalog, 'limited': limited,
            'catalog_warning': warning, 'project_url': body.project_url}


_ICON_SCAN_CACHE: dict[str, tuple[float, dict]] = {}
_ICON_SCAN_LOCK = threading.Lock()


@app.post('/api/project/icons')
def project_icons(req: Request, payload: ProjectIconSearch):
    require_write(req)
    # Avoid exhausting unauthenticated GitHub API limits when revisiting a
    # configuration; the explicit refresh button always bypasses the cache.
    with _ICON_SCAN_LOCK:
        saved = _ICON_SCAN_CACHE.get(payload.project_url)
        if not payload.refresh and saved and saved[0] > time.monotonic():
            return saved[1]
    result = _project_icon_candidates(payload.project_url)
    with _ICON_SCAN_LOCK:
        if len(_ICON_SCAN_CACHE) >= 30:
            _ICON_SCAN_CACHE.clear()
        _ICON_SCAN_CACHE[payload.project_url] = (time.monotonic() + 600, result)
    return result

def _project_info(original: str, resolved: str, data: dict) -> tuple[str, str, list[str]]:
    """Project link + icon. Never guess an image on an unrelated site."""
    meta_icon = (data.get("x-casaos") or {}).get("icon") if isinstance(data.get("x-casaos"), dict) else ""
    if not isinstance(meta_icon, str) or not meta_icon.startswith("https://"):
        meta_icon = ""
    original_parts = urllib.parse.urlsplit(original)
    resolved_parts = urllib.parse.urlsplit(resolved)
    owner = repo = ""
    if original_parts.hostname == "github.com":
        sections = original_parts.path.strip("/").split("/")
        if len(sections) >= 2:
            owner, repo = sections[:2]
    elif resolved_parts.hostname == "raw.githubusercontent.com":
        sections = resolved_parts.path.strip("/").split("/")
        if len(sections) >= 3:
            owner, repo = sections[:2]
    if original_parts.hostname in _GITEA_PUBLIC_HOSTS:
        pieces = original_parts.path.strip('/').split('/')
        if len(pieces) >= 2 and all(GITHUB_PART.fullmatch(x) for x in pieces[:2]):
            return f"https://{original_parts.hostname}/{pieces[0]}/{pieces[1]}", meta_icon, []
    if original_parts.hostname == 'codeberg.org':
        pieces = original_parts.path.strip('/').split('/')
        if len(pieces) >= 2 and all(GITHUB_PART.fullmatch(part) for part in pieces[:2]):
            return f"https://codeberg.org/{pieces[0]}/{pieces[1]}", meta_icon, []
    if not (GITHUB_PART.fullmatch(owner) and GITHUB_PART.fullmatch(repo)):
        return "", meta_icon, []
    project = f"https://github.com/{owner}/{repo}"
    if meta_icon:
        return project, meta_icon, ["Icon aus den Original-Compose-Metadaten übernommen."]
    try:
        metadata = _github_json(f"https://api.github.com/repos/{owner}/{repo}")
        branch = metadata.get("default_branch")
        if not isinstance(branch, str) or not branch:
            return project, meta_icon, []
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{urllib.parse.quote(branch, safe='')}"
        if isinstance(metadata.get("size"), int) and metadata["size"] > 50000:
            tree = _github_json(tree_url)
        else:
            try:
                tree = _github_json(tree_url + "?recursive=1")
                if tree.get("truncated"):
                    tree = _github_json(tree_url)
            except HTTPException as exc:
                if exc.status_code != 400 or "Quell-Datei ist zu groß" not in str(exc.detail):
                    raise
                tree = _github_json(tree_url)
        found = _github_logo(owner, repo, branch, tree)
        if found:
            return project, found, ["App-Icon aus dem Original-GitHub-Repository erkannt."]
    except (HTTPException, OSError, ValueError):
        pass  # A missing logo must never prevent source analysis.
    return project, meta_icon, (["Icon aus Compose-Metadaten übernommen."] if meta_icon else [])


# Verified publisher image and host-network requirement from
# https://www.music-assistant.io/installation/ (Docker Compose section).
# This is a targeted fallback for the upstream repository without a Compose file.
OFFICIAL_REPO_TEMPLATES = {
    # Official Home Assistant Container docs:
    # https://www.home-assistant.io/installation/linux/#install-home-assistant-container
    # Home Assistant Core source repository has a Dockerfile but is not the
    # published docker-compose distribution.  Do not infer build instructions
    # or install an arbitrary image; this verified publisher template is the
    # documented container deployment, not an upstream repository compose.
    "home-assistant/core": """name: homeassistant
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: unless-stopped
    stop_grace_period: 60s
    network_mode: host
    privileged: true
    environment:
      TZ: Europe/Berlin
    volumes:
      - /DATA/AppData/homeassistant/config:/config
x-casaos:
  main: homeassistant
  port_map: '8123'
""",
    "music-assistant/server": """name: music-assistant-server
services:
  music-assistant-server:
    image: ghcr.io/music-assistant/server:latest
    container_name: music-assistant-server
    restart: unless-stopped
    network_mode: host
    volumes:
      - /DATA/AppData/music-assistant-server/data:/data
    environment:
      LOG_LEVEL: info
""",
}


# Verified against the publisher's Getting Started / Configuration wiki.
# This is a conservative draft for the wizard, NOT an original repository Compose.
# Persistent database and custom server configuration must be set up separately.
FILEBROWSER_QUANTUM_TEMPLATE = """name: filebrowser
services:
  filebrowser:
    image: ghcr.io/gtsteffaniak/filebrowser:stable
    restart: unless-stopped
    ports:
      - '8080:80'
    volumes:
      - /DATA/AppData/filebrowser/files:/srv
      - /DATA/AppData/filebrowser/data:/home/filebrowser/data
    environment:
      FILEBROWSER_DATABASE_PATH: /home/filebrowser/data/database.sqlite
      FILEBROWSER_ADMIN_PASSWORD: ''
      FILEBROWSER_JWT_TOKEN_SECRET: ''
"""


def _prepare_filebrowser_compose(content: str) -> str:
    """Fill *new* secrets in publisher draft, never copy public example values.

    Called only for our verified FileBrowser Quantum publisher draft. User-entered
    secrets on subsequent wizard stages remain intact.
    """
    doc = safe_yaml(content)
    for service in doc['services'].values():
        if service.get('image') != 'ghcr.io/gtsteffaniak/filebrowser:stable':
            continue
        environment = service.get('environment')
        if not isinstance(environment, dict):
            continue
        for key in ('FILEBROWSER_ADMIN_PASSWORD', 'FILEBROWSER_JWT_TOKEN_SECRET'):
            if not environment.get(key):
                environment[key] = secrets.token_urlsafe(36)
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _filebrowser_publisher_draft() -> tuple[str, str, list[str]]:
    return (_prepare_filebrowser_compose(FILEBROWSER_QUANTUM_TEMPLATE),
            'https://github.com/gtsteffaniak/filebrowser/wiki/Getting-Started',
            ['Dokumentierte FileBrowser-Quantum-Vorlage erzeugt; keine Original-Compose aus dem Repository.',
             'Container-Port 80, vorgeschlagener Host-Port 8080; Portkonflikte vor Installation prüfen.',
             'Datenbank liegt persistent unter /DATA/AppData/filebrowser/data.',
             'Ein neues Administratorpasswort und JWT-Secret wurden kryptografisch zufällig erzeugt.',
             'Dateiverzeichnis ist nach /srv eingebunden; Dateien und Berechtigungen vorab prüfen.',
             'Keine automatischen Root-Rechte. Falls der Container Schreibrechte benötigt, '
             'Besitzer bzw. Berechtigungen gezielt prüfen.',
             'Generierte Geheimnisse in der Compose-Vorschau schützen; '
             'vor öffentlicher Freigabe weitere Authentifizierungsmaßnahmen prüfen.'])


# Verified publisher deployment source, not a static guessed recipe.
# https://github.com/koush/scrypted/blob/main/install/docker/docker-compose.yml
# https://docs.scrypted.app/install/linux-docker.html
_SCRYPTED_OFFICIAL_COMPOSE = (
    'https://raw.githubusercontent.com/koush/scrypted/main/install/docker/docker-compose.yml'
)


def _im_scrypted_official_compose() -> tuple[str, str, list[str]] | None:
    """Fetch the actual upstream Compose, then supplement only documented UI metadata.

    For ZimaOS host-network deployments, the WebUI's fixed HTTPS 10443 port
    must be explicit: it cannot be inferred from `ports:` (there are none).
    Fail closed when the publisher changed the expected service or image.
    """
    try:
        source = _download_remote(_SCRYPTED_OFFICIAL_COMPOSE)
        validate_source, _ = _resolve_compose_variables(source)
        doc = safe_yaml(validate_source)
    except (HTTPException, ValueError, yaml.YAMLError):
        return None
    main = doc['services'].get('scrypted')
    if (not isinstance(main, dict)
            or main.get('network_mode') != 'host'
            or not isinstance(main.get('image'), str)
            or main['image'].split('@', 1)[0].split(':', 1)[0] != 'ghcr.io/koush/scrypted'):
        return None
    existing = doc.get('x-casaos')
    if existing is not None and not isinstance(existing, dict):
        return None
    if isinstance(existing, dict) and existing:
        # Publisher metadata wins; never quietly replace explicit settings.
        if (existing.get('main') != 'scrypted'
                or str(existing.get('port_map', '')) != '10443'):
            return None
    else:
        # Append, rather than reserialize, to retain all upstream comments,
        # examples and security warnings in the source preview.
        source = source.rstrip() + (
            "\n\nx-casaos:\n"
            "  main: scrypted\n"
            "  port_map: '10443'\n"
            "  scheme: https\n"
        )
    notes = [
        'Offizielle Scrypted-Compose in install/docker/docker-compose.yml gefunden (Branch main).',
        'Hersteller-Image ghcr.io/koush/scrypted; Host-Netzwerk und HTTPS-Weboberfläche auf Port 10443 erkannt.',
        'ZimaOS-WebUI-Metadaten (x-casaos: main, port_map, https) ergänzt; keine Container-Ports erfunden.',
        'Das Hersteller-Compose enthält Watchtower mit /var/run/docker.sock und automatischen Updates. '
        'Dieser Dienst hat weitreichenden Docker-Zugriff und sollte vor der Installation bewusst geprüft werden; '
        'wenn Update Monitor die Updates übernimmt, Watchtower und die Scrypted-WebHook-Updatevariablen im Entwurf entfernen.',
        'Watchtower-Token und Scrypted-WebHook-Autorisierung müssen übereinstimmen und dürfen keine veröffentlichten Beispielwerte behalten.',
        'Bei Host-Netzwerk ist der Web-Port 10443 nur ein Teil der möglichen Portnutzung; '
        'mDNS/Avahi und vorhandene Kameradienste gegebenenfalls separat prüfen.',
        'Der Datenordner ./volume wird im Konfigurationsschritt in den gemeinsamen ZimaOS-AppData-Pfad übertragen.',
        'Die Originaldatei wurde abgerufen und syntaktisch geprüft. Das beweist noch keinen erfolgreichen ZimaOS-Start.',
    ]
    return source, _SCRYPTED_OFFICIAL_COMPOSE, notes


def _publisher_template(owner: str, repo: str) -> tuple[str, str, list[str]] | None:
    key = f"{owner.lower()}/{repo.lower()}"
    content = OFFICIAL_REPO_TEMPLATES.get(key)
    if content is None:
        return None
    if key == 'home-assistant/core':
        return content, 'https://www.home-assistant.io/installation/linux/', [
            'Keine geeignete Installations-Compose im Quellcode-Repository. '
            'Stattdessen Vorlage aus der offiziellen Home Assistant Container-Anleitung vorbereitet.',
            'Offizielles Image: ghcr.io/home-assistant/home-assistant:stable. '
            'Kein lokaler Build aus home-assistant/core erforderlich.',
            'Host-Netzwerk: Home Assistant benötigt standardmäßig TCP 8123. '
            'Es gibt keine ports:-Weiterleitung; vorhandene Belegung wird geprüft.',
            'Konfiguration liegt unter /DATA/AppData/homeassistant/config; '
            'vorhandene Home-Assistant-Konfigurationen nicht ungeprüft überschreiben.',
            'Die offizielle Docker-Anleitung verwendet privileged: true. '
            'Das gewährt weitreichenden Host-Zugriff; vor Installation bestätigen.',
            'Optional: /run/dbus:/run/dbus:ro für Bluetooth ergänzen, '
            'aber nur wenn die D-Bus-Quelle auf dem NAS vorhanden ist.',
            'Home Assistant Container ist nicht Home Assistant OS; '
            'Supervisor und Home-Assistant-OS-Apps stehen hier nicht zur Verfügung.',
            'Wichtig: Falls Home Assistant schon auf dem NAS läuft, '
            'keine zweite Installation erstellen oder bestehende Daten verändern.',
        ]
    return content, '', [
        'Keine Compose-Datei im Repository. Verifizierte offizielle Docker-Installationsvorlage verwendet.',
        'Music Assistant benötigt network_mode: host für mDNS/UPnP und lokale Lautsprecher.',
        'Weboberfläche: NAS-IP:8095; Audio-Streaming verwendet standardmäßig TCP 8097.',
        'Vor der Installation prüfen, ob Music Assistant bereits auf dem NAS läuft.',
    ]

# Documentation fallback is used ONLY if GitHub has no deployable Compose.
# The source is the publisher's own repository, never an arbitrary external blog.
_DOCKER_GUIDES = ('docker.md', 'docs/docker.md', 'docs/installation.md',
                  'docs/install.md', 'README.md')
# Keeps provenance across Source -> Plan -> Install. Never sent to ZimaOS.
_DOC_IMAGE_PREFLIGHT = 'x-install-monitor-documentation-images'
_DOC_FENCE = re.compile(r'```([^\n`]*)\n(.*?)\n```', re.S)
_DOCKER_OPTION_WITH_VALUE = {
    '--name': 'name', '--device': 'devices', '--cap-add': 'cap_add',
    '-p': 'ports', '--publish': 'ports', '-v': 'volumes', '--volume': 'volumes',
    '-e': 'environment', '--env': 'environment', '--restart': 'restart',
    '--network': 'network_mode', '--user': 'user', '--hostname': 'hostname',
}


def _compose_from_documented_run(block: str, repo: str) -> dict | None:
    """Parse a restricted docker run snippet, without executing shell content.

    Unsupported flags/commands are rejected so an unsafe/incomplete launch is
    never suggested as equivalent to the publisher's documented invocation.
    """
    lines = block.strip().splitlines()
    commands = []
    current = ''
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('$ '):
            line = line[2:]
        current = (current + ' ' + line).strip()
        if current.endswith('\\'):
            current = current[:-1].rstrip()
            continue
        commands.append(current)
        current = ''
    if current:
        return None
    # Only a single, complete docker run command is a safe source of a stack.
    if len(commands) != 1 or not commands[0].startswith('docker run '):
        return None
    command = commands[0]
    if any(c in command for c in ('$', '`', ';', '|', '&', '>', '<', '\x00')):
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    if tokens[:2] != ['docker', 'run']:
        return None
    service = {'restart': 'unless-stopped'}
    name = ''
    i = 2
    while i < len(tokens):
        arg = tokens[i]
        if arg in ('-d', '--detach'):
            i += 1
            continue
        if arg in ('-it', '-i', '-t', '--interactive', '--tty'):
            # interactive terminals are unsuitable for persistent ZimaOS apps.
            return None
        if arg.startswith('-'):
            option, sep, embedded = arg.partition('=')
            if option not in _DOCKER_OPTION_WITH_VALUE:
                return None
            if sep:
                val = embedded
                i += 1
            else:
                if i + 1 >= len(tokens):
                    return None
                val = tokens[i + 1]
                i += 2
            if not val or val.startswith('-'):
                return None
            key = _DOCKER_OPTION_WITH_VALUE[option]
            if key == 'name':
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,70}', val):
                    return None
                name = val
            elif key in ('devices', 'ports', 'volumes', 'cap_add', 'environment'):
                if key == 'devices' and not re.fullmatch(r'/dev/[A-Za-z0-9_./:-]+', val):
                    return None
                if key == 'ports' and not re.fullmatch(r'(?:(?:127\.0\.0\.1|0\.0\.0\.0):)?[0-9]{1,5}:[0-9]{1,5}(?:/(?:tcp|udp))?', val):
                    return None
                if key == 'volumes':
                    pieces = val.split(':')
                    if len(pieces) not in (2, 3) or not pieces[1].startswith('/') or not pieces[0]:
                        return None
                    source = pieces[0]
                    if source.startswith('./'):
                        # Never store relative mount data in the temporary build directory.
                        suffix = source[2:].strip('/')
                        if not suffix or '..' in suffix.split('/'):
                            return None
                        pieces[0] = '/DATA/AppData/' + repo + '/' + suffix
                        val = ':'.join(pieces)
                    elif not source.startswith('/') or '..' in source.split('/'):
                        return None
                if key == 'cap_add' and not re.fullmatch(r'[A-Z_]+', val):
                    return None
                if key == 'environment' and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*=.{0,500}', val):
                    return None
                service.setdefault(key, []).append(val)
            else:
                if key == 'network_mode' and val not in ('bridge', 'host'):
                    return None
                if key == 'restart' and val not in ('always', 'unless-stopped', 'no', 'on-failure'):
                    return None
                service[key] = val
            continue
        # The first positional value is the Docker image. Arbitrary command
        # arguments after it could be required, so do not silently discard them.
        if not IMAGE.fullmatch(arg) or i != len(tokens) - 1:
            return None
        service['image'] = arg
        i += 1
    if 'image' not in service:
        return None
    service_name = slug(repo)
    if name:
        service['container_name'] = name
    # Host networking requires publisher-specific port knowledge which cannot
    # be validated by the generic installer; do not fabricate a working setup.
    if service.get('network_mode') == 'host':
        return None
    return {'name': service_name, 'services': {service_name: service}}


# Repository-wide discovery. Index every reachable path, not just familiar
# Docker/deploy folders. The GitHub tree API can truncate giant repositories;
# in that case walk each subtree by SHA. The limits are resource safeguards,
# never evidence that an installation recipe does not exist.
_GITHUB_SCAN_DIRS = ('container', '_docker', '.docker', 'docker', 'compose', 'deploy', 'deployment', 'deployments',
                     'install', 'installation', 'docs', 'documentation', 'infra', 'infrastructure', 'config',
                     'containers', 'selfhost', 'self-hosted', 'packaging', 'examples', 'scripts', 'services', 'app', 'server')
_GITHUB_SKIP_PARTS = {'node_modules', '.git', '.github', 'vendor', 'target',
                      'dist', 'build', '__pycache__', 'tests', 'test', 'fixtures',
                      'fixture', 'helm', 'charts', 'k8s', 'kubernetes',
                      '.devcontainer', '.vscode', '.circleci', '.ci', 'ci',
                      'e2e', '__tests__', 'localdev', 'benchmark', 'benchmarks',
                      'playwright', 'cypress', 'debug'}
_GITHUB_EXAMPLE_DIRS = {'examples', 'example', 'samples', 'sample', 'demo', 'demos'}
# An unauthed GitHub API has only 60 requests/hour. Do not silently exhaust it.
_GITHUB_SCAN_MAX_TREES = 400  # authenticated; smaller budget without a token
_GITHUB_SCAN_MAX_FILES = 180000
_GITHUB_PROBE_MAX_YAMLS = 140
_GITHUB_PROBE_MAX_DOCS = 24
_GITHUB_PROBE_MAX_SCRIPTS = 16


# A full GitHub scan can outlast a normal reverse-proxy HTTP request. Progress
# lives only in memory and never triggers an installation or executes scripts.
_IM_SCAN_JOBS: dict[str, dict] = {}
_IM_SCAN_JOB_LOCK = threading.RLock()
_IM_SCAN_THREAD = threading.local()
_IM_SCAN_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix='im-repo-scan')


def _im_scan_progress(message: str) -> None:
    job_id = getattr(_IM_SCAN_THREAD, 'job_id', None)
    if not job_id:
        return
    with _IM_SCAN_JOB_LOCK:
        job = _IM_SCAN_JOBS.get(job_id)
        if job and job['status'] in ('queued', 'running'):
            job['progress'] = message[:400]
            job['status'] = 'running'



def _safe_github_index_path(path: str) -> bool:
    return (bool(path) and len(path) <= 700 and not path.startswith('/')
            and not any(c in path for c in ('\\', ':', '?', '#', '\x00'))
            and all(part not in ('', '.', '..') for part in path.split('/')))


def _github_tree_directory_score(path: str) -> int:
    """Prioritize likely deployments but NEVER discard other directories."""
    if not _safe_github_index_path(path):
        return -1
    parts = path.lower().split('/')
    score = 100 - min(len(parts), 15) * 4
    if any(p in _GITHUB_SCAN_DIRS for p in parts):
        score += 120
    if any(p in ('docker', '_docker', 'install', 'deployment', 'deploy') for p in parts):
        score += 100
    if any(p in _GITHUB_SKIP_PARTS for p in parts):
        score -= 100
    return score


def _github_repository_files(base: str, branch: str, repository_size: int) -> tuple[set[str], bool]:
    """Index all reachable GitHub file paths; report incomplete scans honestly.

    Fast path: GitHub's recursive Git Trees API (one request, all directories).
    Fallback: traverse all folder SHAs including unfamiliar/deep paths. Nothing
    is executed and binary/source blobs are NOT downloaded en masse; the later
    content stage reads only plausible deployment instructions/Compose files.
    """
    from heapq import heappush, heappop
    tree_url = base + '/git/trees/' + urllib.parse.quote(branch, safe='')
    _im_scan_progress('GitHub-Verzeichnisbaum wird vollständig eingelesen …')
    token_configured = bool(_gh_token())
    # One unauthenticated scan must not exhaust the 60-request hourly GitHub
    # quota. Large/truncated repositories are incomplete until token enabled.
    request_budget = _GITHUB_SCAN_MAX_TREES if token_configured else 8
    try:
        data = _github_json(tree_url + '?recursive=1')
        if not data.get('truncated') and isinstance(data.get('tree'), list):
            result = {item['path'] for item in data['tree']
                      if isinstance(item, dict) and item.get('type') == 'blob'
                      and isinstance(item.get('path'), str)
                      and _safe_github_index_path(item['path'])}
            submodules = any(isinstance(i, dict) and i.get('type') == 'commit'
                             for i in data['tree'])
            _im_scan_progress(f'GitHub-Verzeichnisbaum erfasst: {len(result)} Dateipfade. Installationsdateien werden gesucht …')
            return result, submodules
    except HTTPException as exc:
        # The recursive response can exceed _github_json's safe download cap.
        # A 2.5MB truncated response is not evidence of an empty repository.
        if 'zu groß' not in str(exc.detail):
            raise

    files: set[str] = set()
    pending: list[tuple[int, int, str, str]] = []
    serial = 0
    incomplete = False
    subtree_cache: dict[str, dict] = {}

    def ingest(tree: dict, prefix: str) -> None:
        nonlocal serial, incomplete
        if tree.get('truncated') or not isinstance(tree.get('tree'), list):
            incomplete = True
        for item in tree.get('tree', []):
            if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                continue
            path = prefix + item['path']
            if not _safe_github_index_path(path):
                incomplete = True
                continue
            if item.get('type') == 'blob':
                files.add(path)
            elif item.get('type') == 'tree' and isinstance(item.get('sha'), str):
                score = _github_tree_directory_score(path)
                serial += 1
                heappush(pending, (-score, serial, path, item['sha']))
            elif item.get('type') == 'commit':  # git submodule, not part of repo
                incomplete = True

    root_tree = _github_json(tree_url)
    ingest(root_tree, '')
    requests_done = 1
    while pending and requests_done < request_budget and len(files) < _GITHUB_SCAN_MAX_FILES:
        _, _, dirname, sha = heappop(pending)
        tree = subtree_cache.get(sha)
        if tree is None:
            try:
                tree = _github_json(base + '/git/trees/' + urllib.parse.quote(sha, safe=''))
            except HTTPException as exc:
                if 'API-Limit' in str(exc.detail):
                    # An API quota failure must be visible and actionable.
                    raise
                incomplete = True
                continue
            subtree_cache[sha] = tree
            requests_done += 1
        # Git permits identical subtree SHAs at multiple distinct paths. The
        # contents are reused, but paths must be expanded under each prefix.
        ingest(tree, dirname + '/')
        if requests_done % 10 == 0:
            _im_scan_progress(f'GitHub-Ordner geprüft: {requests_done}; Dateien erfasst: {len(files)}; offene Ordner: {len(pending)}')
    if pending or len(files) >= _GITHUB_SCAN_MAX_FILES:
        incomplete = True
    return files, incomplete


def _im_official_zimaos_path(path: str, repo: str) -> bool:
    """Publisher-hosted native recipe, not a generic root development stack.

    An application-specific folder prevents unrelated nested deployment
    examples from outranking the actual publisher application.
    """
    parts = path.lower().split('/')
    app = repo.lower().replace('_', '-')
    folders = [part.replace('_', '-') for part in parts[:-1]]
    return (
        (parts[-1] in ('compose.yml', 'compose.yaml', 'docker-compose.yml', 'docker-compose.yaml'))
        and len(parts) >= 3
        and ('zimaos' in folders or 'casaos' in folders)
        and (app in folders or (folders[-1] in ('zimaos', 'casaos')
                                 and app in parts[-1].replace('_', '-')))
    )


def _github_deploy_score(path: str, repo: str) -> int:
    """Rank YAML for a bounded read-and-parse probe, including generic names.

    We never trust file names alone: _discover_github_repository verifies each
    candidate with safe_yaml and rejects unrelated YAML such as CI workflows.
    """
    if not _safe_github_index_path(path):
        return -1
    parts = path.lower().split('/')
    if any(part in _GITHUB_SKIP_PARTS for part in parts[:-1]):
        return -1
    # Includes test_foo, e2e-proxy, compose.e2e.yml, and docker-compose-tests.
    # Without this early check, fallback scoring could accept a test-only YAML.
    if re.search(r"(?:^|[/._-])(dev|test|tests|testing|ci|e2e|unit|integration|localdev|benchmark|benchmarks|playwright|cypress)(?:$|[/._-])", path.lower()):
        return -1
    legacy = _compose_score(path)
    if legacy >= 0:
        # Deeply nested generic Compose files often belong to a bundled
        # example, test dependency, or a different subproject. A working root
        # compose should outrank them unless an explicit ZimaOS/production
        # variant is evidenced. This only changes ranking, not installation.
        depth_penalty = min(path.count('/') * 25, 125)
        priority = legacy + 150 - depth_penalty
        if _im_official_zimaos_path(path, repo):
            priority += 400  # Explicit vendor ZimaOS bundle precedes root Compose.
        # The publisher may document a pre-built release stack next to the
        # source/developer Compose. Read image-tag variants early so a large
        # repository scan does not exhaust its deadline on a build-only root.
        # A filename is only a *hint*: content and repository identity are
        # verified below before any candidate is selected.
        if parts[-1] in ('docker-compose-image-tag.yml', 'docker-compose-image-tag.yaml',
                         'compose-image-tag.yml', 'compose-image-tag.yaml'):
            priority += 125
        if any(folder in _GITHUB_EXAMPLE_DIRS for folder in parts[:-1]):
            # Many upstream projects publish their *actual* installation in
            # example/<project>/compose.yaml. Rank such files, never discard
            # them solely because the directory is named 'example'.
            priority -= 30
            if any(part.replace('_', '-') == repo.lower().replace('_', '-')
                   for part in parts[:-1]):
                priority += 95
        return priority
    low = path.lower()
    parts = low.split('/')
    filename = parts[-1]
    if (not filename.endswith(('.yml', '.yaml'))
        or any(part in _GITHUB_SKIP_PARTS for part in parts[:-1])
        ):
        return -1
    basename = filename.rsplit('.', 1)[0]
    excluded = ('override', 'config', 'values', 'variables', 'requirements',
                'dependabot', 'action', 'package', 'lint', 'pre-commit',
                'renovate', 'example-env', 'settings')
    if any(x in basename.split('-') or x in basename.split('_') for x in excluded):
        return -1
    if re.search(r'(?:^|[/._-])(test|dev|ci|fixture|beta)(?:$|[/._-])', low):
        return -1
    score = 8 - min(path.count('/') * 6, 75)
    app = repo.lower().replace('_', '-')
    if basename.replace('_', '-') == app:
        score += 75
    elif basename.replace('_', '-').startswith(app + '-'):
        score += 55
    if basename in ('app', 'application', 'services', 'production', 'prod', 'docker', 'deploy', 'installation', 'install'):
        score += 30
    if any(part in _GITHUB_SCAN_DIRS for part in parts[:-1]):
        score += 27
    if any(part in _GITHUB_EXAMPLE_DIRS for part in parts[:-1]):
        score -= 35
        if any(part.replace('_', '-') == app for part in parts[:-1]):
            score += 95
    if basename in ('default', 'config', 'values'):
        score -= 30
    return score



def _im_readme_compose_references(owner: str, repo: str, branch: str,
                                   files: set[str]) -> set[str]:
    """Find explicit Compose paths in the publisher README, without executing it.

    Only accept an actual path from the indexed repository; the README cannot
    introduce arbitrary URLs, non-GitHub origins or path traversal.
    """
    readme = next((p for p in ('README.md', 'README.markdown', 'readme.md')
                   if p in files), None)
    if not readme:
        return set()
    url = 'https://raw.githubusercontent.com/' + '/'.join(
        urllib.parse.quote(x, safe='') for x in (owner, repo, branch, readme))
    try:
        content = _download_remote(url, max_bytes=180000)
    except HTTPException:
        return set()
    regex = re.compile(
        r'(?<![A-Za-z0-9_./-])((?:[A-Za-z0-9_.-]+/){0,14}'
        r'(?:docker-compose|compose)[A-Za-z0-9_.-]*\.ya?ml)', re.I)
    found = set()
    for match in regex.finditer(content):
        path = match.group(1).lstrip('./')
        if _safe_github_index_path(path) and path in files:
            found.add(path)
    return found


def _im_repo_matches_compose(doc: dict, repo: str) -> bool:
    """Do not confuse a bundled proxy/database demonstration with the app."""
    expected = repo.casefold().replace('_', '-')
    if str(doc.get('name', '')).casefold().replace('_', '-') == expected:
        return True
    for service_name, service in (doc.get('services') or {}).items():
        if not isinstance(service, dict):
            continue
        if str(service_name).casefold().replace('_', '-') == expected:
            return True
        image = str(service.get('image') or '').split('@', 1)[0].split(':', 1)[0]
        if image.rsplit('/', 1)[-1].casefold().replace('_', '-') == expected:
            return True
    return False


def _im_compose_candidate_quality(doc: dict) -> int:
    """Bounded deployability signal, never a claim of successful installation.

    Prefer complete published-image recipes to local builds or YAML documents
    requiring unavailable sibling files, while keeping repository path scoring
    authoritative. A normal multi-service stack is not a penalty.
    """
    services = doc.get('services', {})
    if not isinstance(services, dict):
        return -45
    ready = 0
    incomplete = 0
    if doc.get('include'):
        incomplete += 4
    for service in services.values():
        if not isinstance(service, dict):
            continue
        if isinstance(service.get('image'), str) and service['image'].strip():
            ready += 1
        if 'build' in service:
            incomplete += 2 if not service.get('image') else 1
        if service.get('extends'):
            incomplete += 3
        if service.get('env_file'):
            incomplete += 1
        for vol in (service.get('volumes') or []):
            if isinstance(vol, str):
                pieces = vol.split(':')
                if len(pieces) < 2:
                    continue
                source, target = pieces[:2]
            elif isinstance(vol, dict) and vol.get('type') == 'bind':
                source, target = str(vol.get('source', '')), str(vol.get('target', ''))
            else:
                continue
            if source.startswith(('./', '../')) and _im_file_mount_expected(source, target):
                incomplete += 1
    # Phase-2 catalog audit: many candidates require local builds even when
    # their publisher ships a self-contained image-based alternative.
    # Prefer published-image definitions within a similar filename class,
    # but never overrule an explicit official ZimaOS variant just for this.
    if not ready:
        return -60 if incomplete else -45
    score = min(ready * 4, 16) - min(incomplete * 8, 40)
    if all(isinstance(s, dict) and bool(s.get('image')) and 'build' not in s
           for s in services.values()) and not doc.get('include'):
        score += 45
    elif any(isinstance(s, dict) and s.get('build') is not None
             for s in services.values()):
        score -= 25
    return score


def _github_guide_score(path: str) -> int:
    if not _safe_github_index_path(path):
        return -1
    low = path.lower()
    parts = low.split('/')
    name = parts[-1]
    if (not name.endswith(('.md', '.markdown'))
        or any(part in _GITHUB_SKIP_PARTS for part in parts[:-1])):
        return -1
    if path in _DOCKER_GUIDES:
        return 250 - _DOCKER_GUIDES.index(path) * 20
    score = 0
    if name in ('readme.md', 'readme.markdown'):
        score = 125 if len(parts) == 1 else 65
    for marker in ('docker', 'compose', 'install', 'deploy', 'container', 'selfhost', 'self-host', 'setup'):
        if marker in name:
            score = max(score, 130 if marker in ('docker', 'compose') else 100)
    if any(part in ('docs', 'documentation') for part in parts[:-1]):
        score += 18
    return score - min((len(parts) - 1) * 8, 25) if score else -1


def _compose_from_docker_guide(owner: str, repo: str, branch: str,
                               paths: set[str]) -> tuple[str, str, list[str]] | None:
    ranked = sorted(((_github_guide_score(path), path) for path in paths),
                    key=lambda x: (-x[0], len(x[1]), x[1]))
    for score, path in [entry for entry in ranked if entry[0] >= 0][:_GITHUB_PROBE_MAX_DOCS]:
        url = 'https://raw.githubusercontent.com/' + '/'.join(
            urllib.parse.quote(x, safe='') for x in (owner, repo, branch, *path.split('/')))
        try:
            markdown = _download_remote(url, max_bytes=200000)
        except HTTPException as exc:
            if 'API-Limit' in str(exc.detail):
                raise
            continue
        for match in _DOC_FENCE.finditer(markdown):
            language, block = match.group(1).strip().lower(), match.group(2)
            if language not in ('sh', 'bash', 'shell', 'console', 'yaml', 'yml', 'docker-compose', ''):
                continue
            doc = None
            if language in ('sh', 'bash', 'shell', 'console', ''):
                doc = _compose_from_documented_run(block, repo)
            if doc is None and language in ('yaml', 'yml', 'docker-compose', ''):
                try:
                    parsed = yaml.safe_load(block)
                    if isinstance(parsed, dict) and isinstance(parsed.get('services'), dict):
                        doc = safe_yaml(block)
                except (yaml.YAMLError, HTTPException):
                    continue
            if doc is None:
                continue
            if not all(isinstance(service.get('image'), str) and not service.get('build')
                       for service in doc['services'].values()):
                continue
            doc[_DOC_IMAGE_PREFLIGHT] = True
            notes = [f'Keine eigenständige Compose-Datei vorhanden: Docker-Anleitung {path} aus dem Original-GitHub-Repository ausgewertet.',
                     'Aus Dokumentation abgeleitete Docker-Images werden vor dem ZimaOS-Installationsauftrag auf Erreichbarkeit geprüft. Fehlende/private Images verhindern die Installation.']
            for service in doc['services'].values():
                devices = service.get('devices') or []
                if any('/dev/kvm' in str(d) for d in devices):
                    notes.append('Virtualisierung erforderlich: Das NAS benötigt /dev/kvm und aktiviertes KVM. Die Anwendung kann eine komplette virtuelle Maschine starten.')
                if any('/dev/net/tun' in str(d) for d in devices):
                    notes.append('Host-Gerät /dev/net/tun und zusätzliche Netzwerkrechte erforderlich. Sicherheit und Netzwerk-Konflikte prüfen.')
            if owner.lower() == 'auxxxilium' and repo.lower() == 'arc':
                notes.append('Arc startet DSM in einer QEMU-VM. DSM kann Datenträger verändern: Nur mit gesicherten Daten und separater virtueller Festplatte testen.')
                notes.append('Die Hersteller-Dockerfile benötigt arc.img. Es wird stattdessen die dokumentierte fertig gebaute Image-Variante gewählt.')
            return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), url, notes
    return None



def _github_compose_from_install_scripts(owner: str, repo: str, branch: str,
                                         paths: set[str]) -> tuple[str, str, list[str]] | None:
    """Resolve Compose files explicitly referenced by checked-in install scripts.

    Never execute scripts or download arbitrary script-linked domains. A static
    same-repository raw GitHub Compose URL or relative path is required.
    """
    scripts = []
    for path in paths:
        if not _safe_github_index_path(path):
            continue
        name = path.rsplit('/', 1)[-1].lower()
        if not name.endswith(('.sh', '.bash', '.ps1', '.py')):
            continue
        if any(part.lower() in _GITHUB_SKIP_PARTS for part in path.split('/')[:-1]):
            continue
        if not any(term in name or term in path.lower() for term in ('install', 'docker', 'deploy', 'setup', 'container', 'compose')):
            continue
        score = 100 - path.count('/') * 8
        if any(term in name for term in ('install', 'docker', 'compose')): score += 45
        scripts.append((score, path))
    scripts.sort(key=lambda x: (-x[0], len(x[1]), x[1]))
    for _, path in scripts[:_GITHUB_PROBE_MAX_SCRIPTS]:
        source_url = 'https://raw.githubusercontent.com/' + '/'.join(
            urllib.parse.quote(x, safe='') for x in (owner, repo, branch, *path.split('/')))
        try:
            text = _download_remote(source_url, max_bytes=180000)
        except HTTPException as exc:
            if 'API-Limit' in str(exc.detail): raise
            continue
        # Extract only literal same-repository raw.githubusercontent.com links.
        prefix = f'https://raw.githubusercontent.com/{owner}/{repo}/'
        links: set[str] = set()
        for url in re.findall(r'https://raw\.githubusercontent\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[^\s"\'`<>]+', text, re.I):
            if not url.startswith(prefix): continue
            rest = url[len(prefix):]
            if not rest.startswith(branch + '/'): continue
            candidate = rest[len(branch)+1:].rstrip(');,')
            if candidate in paths and _safe_github_index_path(candidate):
                links.add(candidate)
        # Parse literal paths from `docker compose -f path.yml` etc.
        for match in re.finditer(r'(?:docker\s+compose\s+(?:-f|--file)\s+|\b)([A-Za-z0-9_./-]*(?:docker-compose|compose)[A-Za-z0-9_.-]*\.ya?ml)\b', text, re.I):
            rel = match.group(1)
            if rel.startswith(('/', '../')): continue
            candidates = [rel, '/'.join(path.split('/')[:-1]+[rel])]
            for candidate in candidates:
                if candidate in paths: links.add(candidate)
        for candidate in sorted(links, key=lambda q:(-_github_deploy_score(q,repo),len(q))):
            if _github_deploy_score(candidate,repo) < 0: continue
            url = 'https://raw.githubusercontent.com/' + '/'.join(
                urllib.parse.quote(x, safe='') for x in (owner,repo,branch,*candidate.split('/')))
            try:
                content = _download_remote(url)
                expanded,_ = _resolve_compose_variables(content)
                safe_yaml(expanded)
            except (HTTPException,ValueError,yaml.YAMLError):
                continue
            return content, url, [f'Installationsskript {path} verweist auf die gültige Compose-Datei {candidate}.',
                                  'Skript nur als Text untersucht; keine Befehle daraus ausgeführt.']
    return None


# v0.2.15: Generic, bounded publisher-documentation fallback. This is only
# reached after repository Compose and documented in-repo Docker instructions
# failed. Never crawl arbitrary URLs, execute shell snippets, or guess an image.
class _IMPublisherDocsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[tuple[str, str]] = []
        self._anchor: str | None = None
        self._anchor_text: list[str] = []
        self._pre_level = 0
        self._pre_parts: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == 'a':
            self._anchor = (data.get('href') or '')[:500]
            self._anchor_text = []
        if tag == 'pre':
            self._pre_level += 1
            if self._pre_level == 1:
                self._pre_parts = []
        elif self._pre_level and tag in ('br',):
            self._pre_parts.append('\n')
        elif self._pre_level and tag == 'span' and 'token-line' in (data.get('class') or ''):
            # Docusaurus/Prism often puts each source line in a separate span.
            if self._pre_parts and not self._pre_parts[-1].endswith('\n'):
                self._pre_parts.append('\n')

    def handle_endtag(self, tag: str) -> None:
        if tag == 'a' and self._anchor is not None:
            self.hrefs.append((self._anchor, ''.join(self._anchor_text)[:120]))
            self._anchor = None
            self._anchor_text = []
        if tag == 'pre' and self._pre_level:
            self._pre_level -= 1
            if not self._pre_level:
                content = ''.join(self._pre_parts).strip()
                if 0 < len(content) <= 65000:
                    self.blocks.append(content)
                self._pre_parts = []

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor_text.append(data)
        if self._pre_level:
            self._pre_parts.append(data)


def _im_public_docs_url(url: str, allowed_host: str = '') -> str:
    """Verify TLS and global DNS for an explicitly linked publisher docs host."""
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or '').lower().rstrip('.')
    if (p.scheme != 'https' or not host or p.username or p.password
            or p.port not in (None, 443) or len(url) > 600
            or not re.fullmatch(r'[a-z0-9.-]{4,253}', host)
            or host in ('localhost', '127.0.0.1')
            or host.endswith(('.local', '.internal', '.test', '.localhost'))
            or (allowed_host and host != allowed_host)):
        raise ValueError('Unzulässige Herausgeber-Dokumentation.')
    # Do not accidentally send requests to self-hosted domains using private IPs.
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('Dokumentationshost ist nicht öffentlich.')
    except (socket.gaierror, ValueError) as exc:
        raise ValueError('Dokumentationshost nicht sicher erreichbar.') from exc
    return urllib.parse.urlunsplit(('https', host, p.path or '/', p.query, ''))


def _im_read_publisher_docs(url: str, host: str) -> str:
    url = _im_public_docs_url(url, host)
    # No HTTP redirects: prevents following a malicious publisher link to a
    # second host after the checked DNS/domain and prevents credential leaks.
    request = urllib.request.Request(url, headers={
        'User-Agent': 'InstallMonitor/0.2.17',
        'Accept': 'text/html, text/plain;q=0.7'})
    class _SameHostDocsRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, old_request, fp, code, msg, headers, new_url):
            try:
                new_url = _im_public_docs_url(new_url, host)
            except ValueError:
                return None
            # Only minimal same-host redirect support; no Authorization header.
            return super().redirect_request(old_request, fp, code, msg, headers, new_url)

    with urllib.request.build_opener(_SameHostDocsRedirect()).open(request, timeout=7) as response:
        if response.status != 200:
            raise ValueError('Unerwartete Dokumentationsantwort.')
        _im_public_docs_url(response.geturl(), host)
        mimetype = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in mimetype:
            raise ValueError('Keine HTML-Dokumentation.')
        body = response.read(750001)
        if len(body) > 750000:
            raise ValueError('Dokumentationsseite zu groß.')
    return body.decode('utf-8-sig')


def _im_publisher_image_refs(markdown: str, owner: str, repo: str) -> set[str]:
    """Accept ONLY explicitly linked official registries in the repo README."""
    refs: set[str] = set()
    for match in re.finditer(r'https://hub\.docker\.com/r/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)', markdown, re.I):
        candidate = match.group(1) + '/' + match.group(2)
        if candidate.split('/')[-1].lower() == repo.lower() and IMAGE.fullmatch(candidate):
            refs.add(candidate + ':latest')
    # GHCR images must be explicitly published in the README, not inferred
    # from GitHub repo identity alone.
    for match in re.finditer(r'\bghcr\.io/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?::[A-Za-z0-9_.-]+)?', markdown, re.I):
        candidate = match.group(0)
        if match.group(2).lower() == repo.lower() and IMAGE.fullmatch(candidate):
            refs.add(candidate if ':' in candidate.rsplit('/', 1)[-1] else candidate + ':latest')
    return refs


def _im_normalize_publisher_document(document: dict, repo: str) -> tuple[dict, list[str]]:
    """Convert *documented placeholders* to editable NAS paths; no host edits."""
    notes: list[str] = []
    for service in document['services'].values():
        env = service.get('environment')
        if isinstance(env, list):
            replaced = [value for value in env if not (isinstance(value, str) and
                         re.search(r'<[A-Za-z_][A-Za-z0-9_]*>\s*=', value))]
            if len(replaced) != len(env):
                service['environment'] = replaced
                notes.append('Optionale Platzhalter für Umgebungsvariablen aus der Herstelleranleitung entfernt.')
        mounts = service.get('volumes')
        if not isinstance(mounts, list):
            continue
        for i, mount in enumerate(mounts):
            if isinstance(mount, dict) and mount.get('type') == 'bind':
                source, target = mount.get('source'), mount.get('target')
                if (isinstance(source, str) and isinstance(target, str)
                        and source.startswith('/path/to/') and not _im_file_mount_expected(source, target)):
                    suffix = target.strip('/').replace('/', '-')
                    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', suffix):
                        continue
                    new_path = f'/DATA/AppData/{repo}/{suffix}'
                    mount['source'] = new_path
                    notes.append(f'Beispielordner {source} für {target} durch {new_path} ersetzt. Speicherort vor Installation anpassen.')
            elif isinstance(mount, str) and mount.startswith('/path/to/') and ':' in mount:
                source, _, rest = mount.partition(':')
                target = rest.split(':', 1)[0]
                suffix = target.strip('/').replace('/', '-')
                if not _im_file_mount_expected(source, target) and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', suffix):
                    new_path = f'/DATA/AppData/{repo}/{suffix}'
                    mounts[i] = new_path + ':' + rest
                    notes.append(f'Beispielordner {source} für {target} durch {new_path} ersetzt. Speicherort vor Installation anpassen.')
    return document, notes


def _compose_from_official_external_docs(owner: str, repo: str, branch: str,
                                         files: set[str], homepage: str = '') -> tuple[str, str, list[str]] | None:
    """Generic official docs chain: GitHub README -> HTTPS docs -> Docker Compose.

    The README identifies the source and published image; pages must use the
    identical docs host. At most four pages are fetched. No search-engine URLs,
    guessed Compose paths, unrelated images or remote shell execution.
    """
    readme_name = next((name for name in ('README.md', 'readme.md', 'Readme.md', 'README.markdown') if name in files), 'README.md')
    readme_url = 'https://raw.githubusercontent.com/' + '/'.join(
        urllib.parse.quote(part, safe='') for part in (owner, repo, branch, readme_name))
    try:
        readme = _download_remote(readme_url, max_bytes=150000)
    except (HTTPException, OSError, ValueError):
        return None
    image_refs = _im_publisher_image_refs(readme, owner, repo)
    if not image_refs:
        return None
    homepage_host = (urllib.parse.urlsplit(homepage).hostname or '').lower().rstrip('.')
    seeds: list[tuple[str, str]] = []
    for title, link in re.findall(r'\[([^\]]{1,130})\]\((https://[^)\s]+)\)', readme, re.I):
        parsed = urllib.parse.urlsplit(link)
        host = (parsed.hostname or '').lower()
        if host in ('github.com', 'hub.docker.com', 'discord.gg', 'github.io', 'ghcr.io'):
            continue
        # Only actual installation/documentation links, preferably under the
        # project's declared official homepage domain.
        if not re.search(r'\b(install|docker|documentation|docs)\b', title + ' ' + parsed.path, re.I):
            continue
        if homepage_host and host not in (homepage_host, 'www.' + homepage_host) and homepage_host != 'www.' + host:
            continue
        try:
            url = _im_public_docs_url(link)
        except ValueError:
            continue
        if not any(u == url for u, _ in seeds):
            seeds.append((url, host))
    if not seeds:
        return None
    # Navigate verified publisher documentation, including category landing pages
    # (e.g. Installation -> Official methods -> Run with Docker). A plain
    # "docker|compose" link-only filter incorrectly rejects these intermediate
    # pages and reports an installable project as unsupported.
    queue: list[tuple[str, str, int]] = [(url, host, 0) for url, host in seeds[:3]]
    seen: set[str] = set()
    attempts = 0
    while queue and attempts < 6:
        url, host, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        attempts += 1
        try:
            html = _im_read_publisher_docs(url, host)
            parser = _IMPublisherDocsParser()
            parser.feed(html)
        except (OSError, ValueError, UnicodeError, urllib.error.HTTPError):
            continue
        for snippet in parser.blocks[:45]:
            if 'services:' not in snippet or 'image:' not in snippet:
                continue
            try:
                doc = safe_yaml(snippet)
            except (HTTPException, yaml.YAMLError, ValueError, TypeError):
                continue
            if not any(_matched_publisher_image(doc, ref) for ref in image_refs):
                continue
            if any('build' in svc and not svc.get('image') for svc in doc['services'].values()):
                continue
            doc, changes = _im_normalize_publisher_document(doc, repo)
            doc[_DOC_IMAGE_PREFLIGHT] = True
            notes = [f'Offizielle Docker-Compose-Vorlage auf der Hersteller-Webseite gefunden: {url}.',
                     'Kein lokaler Build notwendig. Hersteller-Compose statt Quellcode-Installation verwendet.',
                     'Sicherheitsprüfung: Ports, Datenordner, Benutzerrechte und Container-Images vor Installation prüfen.']
            notes.extend(changes)
            return (yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), url, notes)
        if depth >= 3:
            continue
        # Restrict hops to the documentation area of the exact publisher host.
        # Only Docker/Compose and relevant installation overview pages qualify.
        # Do not walk unrelated "Community", "Help", "GitHub" or external links.
        origin_path = urllib.parse.urlsplit(seeds[0][0]).path
        root = origin_path.strip('/').split('/')[0].lower()
        if root not in ('docs', 'documentation', 'guide', 'guides', 'installation', 'install'):
            root = 'docs'
        followups: list[tuple[int, str]] = []
        for href, label in parser.hrefs:
            joined = urllib.parse.urljoin(url, href)
            parsed = urllib.parse.urlsplit(joined)
            path = parsed.path.lower().rstrip('/')
            if not (path == '/' + root or path.startswith('/' + root + '/')):
                continue
            clue = (label + ' ' + path).lower()
            if re.search(r'docker|compose', clue):
                priority = 0
            elif re.search(r'official[ -]?methods|official[ -]?installation|installation[ -]?methods', clue):
                priority = 1
            elif (re.search(r'install|getting[ -]?started|setup', clue)
                  and ('category' in path or re.search(r'install|setup', path))):
                priority = 2
            else:
                continue
            try:
                candidate = _im_public_docs_url(joined, host)
            except ValueError:
                continue
            if candidate not in seen and candidate != url:
                followups.append((priority, candidate))
        # Docker links first, followed by official methods category pages.
        # Do not queue unbounded navigation: three deep, six pages total.
        followups.sort(key=lambda x: (x[0], len(x[1]), x[1]))
        for _, candidate in followups[:6]:
            if not any(q == candidate for q, _, _ in queue):
                queue.append((candidate, host, depth + 1))
    return None


def _diagnose_non_docker_repository(owner: str, repo: str, branch: str,
                                    files: set[str], limited: bool) -> dict:
    """Classify non-Compose projects from *evidence*, never from a guessed command.

    Only inspected after all supported Docker deployment candidates fail.
    All sources are public repository text, read-only and bounded. The result
    is informational and must never invoke a package manager automatically.
    """
    readme_path = next((p for p in ('README.md', 'README.markdown', 'readme.md', 'Readme.md')
                        if p in files), '')
    readme = ''
    if readme_path:
        url = 'https://raw.githubusercontent.com/' + '/'.join(
            urllib.parse.quote(x, safe='') for x in (owner, repo, branch, readme_path))
        try:
            readme = _download_remote(url, max_bytes=150000)[:150000]
        except HTTPException as exc:
            if 'API-Limit' in str(exc.detail):
                raise
    text = readme.lower()
    file_lower = {p.lower() for p in files}
    evidence = []
    if readme_path:
        evidence.append(readme_path)
    documentation_url = ('https://github.com/' + '/'.join(
        urllib.parse.quote(p, safe='') for p in (owner, repo)) + '/blob/' +
        urllib.parse.quote(branch, safe='') + '/' + urllib.parse.quote(readme_path, safe='/')
        if readme_path else f'https://github.com/{owner}/{repo}')

    def result(kind: str, title: str, explanation: str, recommendation: str,
               command: str = '') -> dict:
        return {'code': 'unsupported_source', 'kind': kind,
                'title': title, 'explanation': explanation,
                'evidence': evidence[:5], 'recommendation': recommendation,
                'command': command, 'documentation_url': documentation_url,
                'scan_limited': bool(limited),
                'message': 'Das Projekt bietet keinen nachgewiesenen Docker-Installationsweg.'}

    sysext_path = next((p for p in sorted(files) if
                        p.lower().startswith(('raw/usr/lib/extension-release.d/',
                                             'usr/lib/extension-release.d/'))
                        and '/extension-release.' in p.lower()), '')
    raw_artifact = any(p.lower().endswith('.raw') for p in files)
    module_indicators = ('zpkg install' in text or 'module store' in text
                         or 'systemd-sysext' in text or 'sys-ext module' in text)
    if module_indicators and (sysext_path or raw_artifact or
                               ('zpkg install' in text and 'module store' in text)):
        evidence.extend([p for p in (sysext_path,) if p])
        matched = re.search(r'(?im)^\s*(?:sudo\s+)?zpkg\s+install\s+([a-zA-Z0-9_][a-zA-Z0-9_.-]{0,79})\s*$',
                            readme)
        # Never offer arbitrary instructions extracted from untrusted Markdown.
        # Module ids must be an identifier, not a path or shell command.
        module_id = matched.group(1) if matched and not matched.group(1).endswith('.raw') else ''
        command = 'zpkg install ' + module_id if module_id else ''
        if module_id:
            evidence.append('README: zpkg install ' + module_id)
        recommendation = ('ZimaOS → Einstellungen → Module Store' +
                          (' → ' + module_id if module_id else '') +
                          '. Alternativ die offizielle Installationsanleitung des Projekts verwenden.')
        return result('zimaos_module', 'Natives ZimaOS-Modul erkannt',
                      'Dieses Projekt liefert ein systemd-sysext-/ZimaOS-Modul statt eines Docker-Images. '
                      'Ein Docker-Compose-Installationsauftrag ist dafür nicht geeignet.',
                      recommendation, command)

    ha_integrations = [p for p in files if re.fullmatch(
        r'custom_components/[a-zA-Z0-9_-]+/manifest\.json', p)]
    if ha_integrations and 'home assistant' in text:
        evidence.extend(sorted(ha_integrations)[:2])
        return result('home_assistant_integration', 'Home-Assistant-Integration erkannt',
                      'Die Dateien gehören zu einer Home-Assistant-Integration und sind keine eigenständige Docker-Anwendung.',
                      'Die Integration über die vom Projekt dokumentierte Home-Assistant-Methode hinzufügen, z. B. HACS oder custom_components. Home Assistant selbst wird dabei nicht neu installiert.')

    if 'chart.yaml' in file_lower and any('/templates/' in p.lower() for p in files):
        evidence.append('Chart.yaml')
        return result('helm_chart', 'Kubernetes/Helm-Paket erkannt',
                      'Das Projekt liefert ein Helm-Chart für Kubernetes, nicht unmittelbar einen Docker-Compose-Stack.',
                      'Die Kubernetes-/Helm-Anleitung verwenden oder beim Herausgeber nach einer Compose-Variante suchen.')

    source_indicators = [('go.mod', 'Go-Quellcode'), ('pyproject.toml', 'Python-Quellcode'),
                         ('cargo.toml', 'Rust-Quellcode'), ('package.json', 'Node.js-Quellcode')]
    present = [(name, desc) for name, desc in source_indicators if name in file_lower]
    if present:
        evidence.extend(name for name, _ in present[:2])
        kind = ', '.join(desc for _, desc in present[:2])
        return result('source_only', 'Quellprojekt ohne nachgewiesenen Docker-Installationsweg',
                      f'Im Repository wurde {kind} gefunden. Es wurde jedoch keine geeignete Docker-Compose-Datei, '
                      'kein vollständig unterstützter Docker-Startbefehl und kein verifiziertes Docker-Image erkannt. '
                      'Aus Quellcode allein lassen sich Ports, Rechte und Datenordner nicht sicher ableiten.',
                      'Die Installationsanleitung und Releases des Herausgebers prüfen. Falls das Projekt ein Docker-Image oder Compose anbietet, dessen Link bzw. Image-Namen verwenden.')

    return result('unknown', 'Installationsart nicht eindeutig ermittelbar',
                  'In den geprüften Dateien wurde keine unterstützte Docker-Compose-Datei, '
                  'kein vollständig nutzbarer Docker-Startbefehl und kein sicherer Docker-Build-Weg gefunden. '
                  'Das bedeutet nicht zwingend, dass das Projekt grundsätzlich nicht installierbar ist.',
                  'Die offizielle Installationsanleitung und Releases prüfen. Ist eine Compose-Datei oder ein Docker-Image dokumentiert, kann dieses direkt eingegeben werden.')


def _im_prefer_documented_publisher_image(content: str, resolved_url: str) -> tuple[str, list[str]]:
    """Use a pre-built *publisher* image when a GitHub repo Compose builds locally.

    Only substitute matching build-only services; leave the original ports,
    networks, env_file, mounts and dependencies intact. Require an exact
    repository-identity image in the author's checked-in Docker guide. Never
    substitute images based on fuzzy search, README prose or other projects.
    """
    u = urllib.parse.urlsplit(resolved_url)
    parts = u.path.strip('/').split('/')
    if u.hostname != 'raw.githubusercontent.com' or len(parts) < 4:
        return content, []
    owner, repo, branch = parts[:3]
    if not all(GITHUB_PART.fullmatch(v) for v in (owner, repo)):
        return content, []
    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError:
        return content, []
    if not isinstance(doc, dict) or not isinstance(doc.get('services'), dict):
        return content, []
    builders = {name for name, svc in doc['services'].items()
                if isinstance(svc, dict) and 'build' in svc and not svc.get('image')}
    if not builders:
        return content, []
    # Documentation is taken only from the same repository and branch, under
    # bounded URLs. Root Compose remains the authority for the other fields.
    candidates = ('docs/docker.md', 'docs/docker-compose.md', 'docs/installation.md',
                  'docs/install.md', 'README.md')
    base = ('https://raw.githubusercontent.com/' +
            '/'.join(urllib.parse.quote(v, safe='') for v in (owner, repo, branch)) + '/')
    image_names = {f'ghcr.io/{owner.lower()}/{repo.lower()}',
                   f'docker.io/{owner.lower()}/{repo.lower()}',
                   f'{owner.lower()}/{repo.lower()}'}
    found = {}
    for path in candidates:
        if len(found) == len(builders):
            break
        try:
            guide = _download_remote(base + path, max_bytes=150000)
        except HTTPException:
            continue
        for match in _DOC_FENCE.finditer(guide):
            if match.group(1).strip().lower() not in ('yaml', 'yml', 'docker-compose', ''):
                continue
            try:
                example = yaml.safe_load(match.group(2))
            except yaml.YAMLError:
                continue
            if not isinstance(example, dict) or not isinstance(example.get('services'), dict):
                continue
            # Do not transfer an image from an unrelated/partial example.
            if set(example['services']) != set(doc['services']):
                continue
            for service_name in builders - found.keys():
                service = example['services'].get(service_name)
                if not isinstance(service, dict) or service.get('build'):
                    continue
                image_name = service.get('image')
                if not isinstance(image_name, str) or not IMAGE.fullmatch(image_name):
                    continue
                bare = image_name.lower().split('@', 1)[0].split(':', 1)[0]
                if bare in image_names:
                    found[service_name] = (image_name, path)
    if not found:
        return content, []
    notes = []
    for svc, (image, path) in found.items():
        doc['services'][svc].pop('build', None)
        doc['services'][svc]['image'] = image
        notes.append(f'{svc}: Statt lokalem Quellcode-Build das offiziell in {path} dokumentierte Hersteller-Image {image} gewählt.')
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), notes


def _inline_github_env_templates(content: str, resolved_url: str) -> tuple[str, list[str]]:
    """Adapt nearby PUBLIC .env.example/.env.sample to explicit environment.

    The ZimaOS API only receives YAML, not adjacent repository files. Public
    configuration constants are safe to inline. Strong *local* secrets are
    generated afresh; external-provider tokens and sample credentials are never
    used as genuine credentials. An unsafe/unparseable required environment
    file remains unresolved, blocking installation in preflight.
    """
    u = urllib.parse.urlsplit(resolved_url)
    if u.hostname != 'raw.githubusercontent.com':
        return content, []
    repo_path = u.path.strip('/').split('/')
    if len(repo_path) < 4:
        return content, []
    directory = '/'.join(repo_path[:-1])
    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError:
        return content, []
    if not isinstance(doc, dict) or not isinstance(doc.get('services'), dict):
        return content, []
    changed = False
    notes: list[str] = []
    generated_secrets: dict[str, str] = {}
    for service_name, service in doc['services'].items():
        if not isinstance(service, dict):
            continue
        env_files = service.get('env_file')
        if not env_files:
            continue
        references = [env_files] if isinstance(env_files, str) else env_files
        if not isinstance(references, list) or len(references) != 1 or not isinstance(references[0], str):
            continue
        reference = references[0].strip()
        if not re.fullmatch(r'(?:\./)?\.[Ee][Nn][Vv](?:\.[A-Za-z0-9_-]{1,25})?', reference):
            continue
        filename = reference.removeprefix('./')
        template = None
        for extension in ('.example', '.sample'):
            # Never read an actual .env from the repository: only documented
            # public examples, same repo/branch/directory, no path traversal.
            url = 'https://raw.githubusercontent.com/' + directory + '/' + filename + extension
            try:
                template = _download_remote(url, max_bytes=32000)
                break
            except HTTPException:
                continue
        if template is None:
            continue
        variables: dict[str, str] = {}
        skipped: list[str] = []
        generated: list[str] = []
        rejected = False
        for raw_line in template.splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.fullmatch(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
            if not match:
                rejected = True
                break
            key, raw_value = match.groups()
            value = raw_value.strip()
            if value.startswith(('"', "'")):
                quote = value[0]
                stop = value.find(quote, 1)
                if stop < 1 or value[stop+1:].strip() and not value[stop+1:].lstrip().startswith('#'):
                    rejected = True
                    break
                value = value[1:stop]
            else:
                # Compose examples often contain documented inline comments:
                # VINYL_PORT=3099 # HTTP port. Avoid interpreting the comment
                # as part of the value while keeping embedded URL # fragments.
                value = re.split(r'\s+#', value, maxsplit=1)[0].strip()
            if len(value) > 1024 or any(c in value for c in ('\x00', '\n', '\r')):
                rejected = True
                break
            if '${' in value or '$(' in value or '`' in value:
                rejected = True
                break
            if key in variables:
                rejected = True
                break
            credential = bool(re.search(r'(?:PASSWORD|PASSWD|SECRET|PRIVATE_KEY|MASTER_KEY|TOKEN|PASSJWT|API_KEY)$', key, re.I))
            if credential:
                if _im_credential_spec(key, doc)['mode'] == 'external' or re.search(r'(?:^|_)(?:OIDC|OAUTH|TWITCH|DISCOGS|HARDCOVER|TMDB|REBRICKABLE|SCREENSCRAPER|BGG)_', key, re.I):
                    skipped.append(key)
                    continue
                if key not in generated_secrets:
                    generated_secrets[key] = (secrets.token_hex(32) if key.upper() == 'PASSJWT'
                                              else _im_generate_local_secret(key, doc))
                variables[key] = generated_secrets[key]
                generated.append(key)
                continue
            # Public examples may contain placeholders: not working app config.
            # Empty optional fields stay out of the runtime configuration.
            if (not value or re.search(r'(?i)(?:^your[_-]|^replace[_-]|^change[_-]|^<[^>]+>$|^\{your)', value)
                    or (value.startswith('Your') and len(value) > 4 and value[4].isupper())):
                skipped.append(key)
                continue
            variables[key] = value
        if rejected:
            notes.append(f'{service_name}: {filename}.example enthält nicht sicher verarbeitbare Einträge; env_file bleibt zur manuellen Prüfung bestehen.')
            continue
        existing = service.get('environment') or {}
        if isinstance(existing, dict):
            merged = {**variables, **existing}
        elif isinstance(existing, list):
            merged = dict(variables)
            for entry in existing:
                if not isinstance(entry, str) or '=' not in entry:
                    rejected = True
                    break
                k, v = entry.split('=', 1)
                merged[k] = v
        else:
            rejected = True
        if rejected:
            continue
        service.pop('env_file', None)
        if merged:
            service['environment'] = merged
        changed = True
        notes.append(f'{service_name}: {filename} mit der öffentlichen Hersteller-Beispieldatei aufgelöst. ' +
                     f'{len(variables)} Werte übernommen, {len(generated)} neue lokale Geheimnisse erzeugt.')
        if generated:
            notes.append(f'{service_name}: Generierte Zugangsdaten sicher aufbewahren und die Compose-Vorschau nicht öffentlich teilen.')
        if skipped:
            notes.append(f'{service_name}: {len(skipped)} optionale oder unbestätigte Variablen nicht übernommen; externe Anbieter-Schlüssel bei Bedarf selbst hinterlegen.')
    if not changed:
        return content, notes
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), notes


def _discover_without_github_api(owner: str, repo: str) -> tuple[str, str, list[str]] | None:
    """Find publisher Compose over raw.githubusercontent.com without API quota.

    Read the public README to discover documented relative Compose paths, then
    probe commonly used deployment directories on main/master. Each candidate
    must parse as a real Compose document. A bounded attempt budget prevents
    an untrusted repository name triggering an unbounded URL scan.
    """
    # API-quota fallback must also find a publisher's official prebuilt-image
    # recipe; otherwise it would choose the source-build root Compose again.
    filenames = ('compose.yaml', 'compose.yml', 'docker-compose.yaml', 'docker-compose.yml')
    image_tag_files = ('docker-compose-image-tag.yml', 'docker-compose-image-tag.yaml',
                       'compose-image-tag.yml', 'compose-image-tag.yaml')
    directories = ('', 'container/', 'containers/', 'docker/', '_docker/', '.docker/',
                   'install/docker/', 'installation/docker/', 'packaging/docker/',
                   'compose/', 'deploy/', 'deployment/', 'deployments/', 'packaging/')
    max_probes = 112
    attempts = 0
    # Test both common branches up front, then prioritize the branch with an
    # accessible README. This avoids 40+ sequential 404s on a master-only repo.
    branches = []
    for branch in ('main', 'master'):
        prefix = 'https://raw.githubusercontent.com/' + '/'.join(
            urllib.parse.quote(x, safe='') for x in (owner, repo, branch)) + '/'
        documented = []
        has_readme = False
        try:
            readme = _download_remote(prefix + 'README.md', max_bytes=180000)
            has_readme = True
            pattern = (r'(?<![A-Za-z0-9_./-])((?:[A-Za-z0-9_.-]+/){0,5}'
                       r'(?:docker-compose|compose)[A-Za-z0-9_.-]*\.ya?ml)')
            for match in re.finditer(pattern, readme, re.I):
                path = match.group(1)
                if (_safe_github_index_path(path)
                        and _github_deploy_score(path, repo) >= 0
                        and path not in documented):
                    documented.append(path)
                if len(documented) >= 20:
                    break
        except HTTPException:
            pass  # Branch missing or README unavailable: try the other branch.
        branches.append((not has_readme, branch, prefix, documented))
    branches.sort(key=lambda item: item[0])
    for _, branch, prefix, documented in branches:
        ordered = sorted(documented, key=lambda path: -_github_deploy_score(path, repo))
        ordered.extend(image_tag_files)  # Only four bounded root probes before generic Compose.
        ordered.extend(directory + filename for directory in directories for filename in filenames)
        checked = set()
        for path in ordered:
            if path in checked or attempts >= max_probes or not _safe_github_index_path(path):
                continue
            checked.add(path)
            attempts += 1
            url = prefix + '/'.join(urllib.parse.quote(p, safe='') for p in path.split('/'))
            try:
                content = _download_remote(url)
                preview, _ = _resolve_compose_variables(content)
                safe_yaml(preview)
            except HTTPException:
                continue
            return content, url, [
                f'Offizielle Docker-Compose-Datei in {path} gefunden (Branch {branch}).',
                'Ohne GitHub-API gefunden und als Compose-Datei geprüft.',
                'Zusätzliche Umgebungsdateien, Datenordner und Portkonflikte vor Installation überprüfen.',
            ]
    return None


def _discover_github_repository(parts: list[str]) -> tuple[str, str, list[str]]:
    owner, repo = parts[:2]
    if not GITHUB_PART.fullmatch(owner) or not GITHUB_PART.fullmatch(repo):
        raise HTTPException(400, 'Ungültiges GitHub-Repository.')
    # The upstream installation instructions live in the GitHub wiki, not
    # necessarily in a checked-in compose.yaml. Avoid a pointless unauthenticated
    # GitHub API call for this explicitly documented publisher integration.
    if owner.lower() == 'gtsteffaniak' and repo.lower() == 'filebrowser':
        return _filebrowser_publisher_draft()
    # This is a verified publisher-image deployment, not a generic fallback:
    # the Core GitHub repository does not ship the Container installation
    # instructions as a ready-to-run Compose file.  Avoid treating that as
    # proof that the project cannot be installed through Docker.
    if owner.lower() == 'home-assistant' and repo.lower() == 'core':
        return _publisher_template(owner, repo)
    if owner.lower() == 'koush' and repo.lower() == 'scrypted':
        official = _im_scrypted_official_compose()
        if official is not None:
            return official
    base = f'https://api.github.com/repos/{owner}/{repo}' 
    try:
        meta = _github_json(base)
    except HTTPException as exc:
        if 'GitHub-API-Limit' not in str(exc.detail):
            raise
        fallback = _discover_without_github_api(owner, repo)
        if fallback is not None:
            return fallback
        for default_branch in ('main', 'master'):
            documented = _compose_from_official_external_docs(
                owner, repo, default_branch, {'README.md'})
            if documented is not None:
                return documented
        raise HTTPException(429,
            'GitHub-API-Limit erreicht. Direkte Suche nach Compose-Dateien '
            'in üblichen Compose-Ordnern einschließlich container/, containers/, docker/, '
            'deploy/ und Compose-Pfaden aus README auf main/master war erfolglos. '
            'Alternativ das offizielle Docker-Image oder einen direkten Compose-Dateilink verwenden. '
            'Keine Installation ohne verifizierte Konfiguration.') from exc
    branch = meta.get('default_branch')
    if not isinstance(branch, str) or not branch or len(branch) > 150:
        raise HTTPException(400, 'GitHub-Hauptbranch konnte nicht bestimmt werden.')
    if owner.lower() == 'music-assistant' and repo.lower() == 'server':
        return _publisher_template(owner, repo)

    try:
        files, limited = _github_repository_files(base, branch, meta.get('size') if isinstance(meta.get('size'), int) else 0)
    except HTTPException as exc:
        # A quota error can happen AFTER the repository metadata request,
        # during the tree traversal. Public raw-file discovery works without
        # consuming the GitHub API quota.
        if 'API-Limit' not in str(exc.detail):
            raise
        fallback = _discover_without_github_api(owner, repo)
        if fallback is not None:
            return fallback
        for default_branch in ('main', 'master'):
            documented = _compose_from_official_external_docs(
                owner, repo, default_branch, {'README.md'})
            if documented is not None:
                return documented
        raise HTTPException(429,
            'GitHub-API-Limit während der Dateisuche erreicht. Die direkte '
            'Compose-Suche ohne API blieb ebenfalls erfolglos. '
            'Bitte eine verifizierte Compose-Datei oder den offiziellen '
            'Image-Namen eingeben.') from exc
    ranked = sorted(((_github_deploy_score(path, repo), path) for path in files),
                    key=lambda x: (-x[0], len(x[1]), x[1]))
    possible_candidates = [entry for entry in ranked if entry[0] >= 0]
    documented = (_im_readme_compose_references(owner, repo, branch, files)
                  if any(any(part in _GITHUB_EXAMPLE_DIRS for part in path.lower().split('/')[:-1])
                         for _, path in possible_candidates) else set())
    # README references promote legitimate publisher examples but do not let
    # unrelated Traefik/SMTP examples automatically become the main app.
    candidates = sorted(possible_candidates,
                        key=lambda item: (-(item[0] + (55 if item[1] in documented else 0)),
                                          len(item[1]), item[1]))[:_GITHUB_PROBE_MAX_YAMLS]
    probe_limited = len(possible_candidates) > len(candidates)
    chosen = None
    other_valid = 0
    _im_scan_progress(f'{len(files)} Dateipfade erfasst; {len(candidates)} mögliche Compose-Dateien werden geprüft …')
    # A repo-wide file index is complete independently of reading every YAML.
    # A bounded content phase prevents huge repositories from appearing stuck.
    probe_started = time.monotonic()
    content_deadline = 65.0
    content_time_limited = False
    early_selected = False
    for candidate_number, (score, path) in enumerate(candidates, 1):
        if time.monotonic() - probe_started > content_deadline:
            content_time_limited = True
            _im_scan_progress(f'YAML-Prüfzeit erreicht; {candidate_number - 1} von {len(candidates)} Kandidaten untersucht.')
            break
        if candidate_number == 1 or candidate_number % 10 == 0:
            _im_scan_progress(f'Compose-Inhalte prüfen: {candidate_number}/{len(candidates)}; {path}')
        url = 'https://raw.githubusercontent.com/' + '/'.join(
            urllib.parse.quote(x, safe='') for x in (owner, repo, branch, *path.split('/')))
        try:
            content = _download_remote(url)
            # Many valid Compose definitions interpolate their image tag.
            # Validate an ephemeral resolved view; keep the original source
            # intact so the normal wizard resolves/shows variables once.
            validation_source, _ = _resolve_compose_variables(content)
            doc = safe_yaml(validation_source)
        except HTTPException as exc:
            if 'API-Limit' in str(exc.detail):
                raise
            continue
        # YAML like jellyfin.yml in zimapp's repository can be a working
        # example for an entirely different application. If a filename is
        # generic/unrelated, only accept it when the Compose itself links the
        # deployment to this repository, or it sits in a deployment folder.
        if _compose_score(path) < 0:
            images = [str(svc.get('image', '')).lower().split('@', 1)[0].split(':', 1)[0]
                      for svc in doc['services'].values()]
            own_image = any(img.rsplit('/', 1)[-1].replace('_', '-') == repo.lower().replace('_', '-')
                            for img in images)
            own_name = str(doc.get('name', '')).lower() == repo.lower()
            own_build = any('build' in svc for svc in doc['services'].values())
            if not (own_image or own_name or (own_build and score >= 25)
                    or score >= 30):
                continue
        publisher_match = _im_repo_matches_compose(doc, repo)
        if _im_official_zimaos_path(path, repo) and not publisher_match:
            # A matching path is not proof of a matching app image.
            continue
        example_path = any(part in _GITHUB_EXAMPLE_DIRS for part in path.lower().split('/')[:-1])
        # Documentation examples may be different apps bundled in this repo.
        # Keep their availability visible, but do not pick such a sidecar in
        # preference to the application's own deployment.
        if example_path and not publisher_match:
            # A README may document several separate deployment projects,
            # such as the main app, traefik and smtp. Those support stacks
            # must never silently replace the publisher's main application.
            infrastructure_names = {'traefik', 'smtp', 'apprise', 'redis', 'valkey',
                                    'postgres', 'postgresql', 'mysql', 'mariadb',
                                    'database', 'db', 'nginx', 'caddy', 'proxy'}
            path_sections = set(path.lower().split('/')[:-1])
            if path not in documented or path_sections & infrastructure_names:
                continue
        score += (55 if path in documented else 0)
        if publisher_match:
            score += 75
        score += _im_compose_candidate_quality(doc)
        # An explicitly named official image-tag recipe is the right choice
        # over the project's development/source build, *provided* all its
        # services really use images and it represents this repository.
        # Preserve all env_file and bind-mount dependencies for honest review.
        if (path.lower().rsplit('/', 1)[-1] in
                ('docker-compose-image-tag.yml', 'docker-compose-image-tag.yaml',
                 'compose-image-tag.yml', 'compose-image-tag.yaml')
                and publisher_match and all(isinstance(svc, dict)
                and isinstance(svc.get('image'), str) and svc['image'].strip()
                and 'build' not in svc for svc in doc['services'].values())):
            score += 105
        x_casaos = doc.get('x-casaos')
        if isinstance(x_casaos, dict) and x_casaos.get('main') in doc['services']:
            score += 18
        if not chosen:
            chosen = (score, path, url, content)
        elif score > chosen[0]:
            chosen = (score, path, url, content)
            other_valid += 1
        else:
            other_valid += 1
        # Once a complete, published-image root Compose was validated, probing
        # 139 extra unrelated YAMLs just makes *every* GitHub analysis hang.
        # The original ZimaOS-first file score has already ranked such files.
        selected = chosen
        if selected:
            _, selected_path, _, selected_content = selected
            if (selected_path == path and path.count('/') == 0 and score >= 310
                    and not any(_im_official_zimaos_path(remaining, repo)
                                for _, remaining in candidates[candidate_number:])):
                if (all(isinstance(svc, dict) and bool(svc.get('image')) and not svc.get('build')
                        for svc in doc['services'].values())
                    and not _im_compose_external_file_issues(doc)):
                    early_selected = True
                    _im_scan_progress(f'Gültige Haupt-Compose-Datei in {path} gefunden; weitere unnötige YAML-Abfragen übersprungen.')
                    break
            # No remaining candidate can beat the best score even with the
            # largest possible quality/metadata bonus (<=79).
            next_item = candidates[candidate_number] if candidate_number < len(candidates) else (-1, '')
            next_base = next_item[0] + (55 if next_item[1] in documented else 0)
            # Remaining file contents can add repository identity / quality.
            if selected[0] > next_base + 155:
                early_selected = True
                break

    if chosen is not None:
        _, path, url, content = chosen
        notes = [f'Docker-Compose-Datei in {path} gefunden (Branch {branch}). Originaldatei analysiert und validiert. Vor der Installation prüfen.',
                 f'GitHub-Index: {len(files)} Dateipfade erfasst; {candidate_number} von {len(candidates)} möglichen Compose-Dateien bis zur Auswahl geprüft.']
        # The source browser must distinguish syntactic Compose success from
        # a fully self-contained install; env_file/include/configs may refer
        # to files outside the YAML that are not fetched or transferred.
        selected_doc = {}
        try:
            resolved_source, _ = _resolve_compose_variables(content)
            selected_doc = safe_yaml(resolved_source)
            dependencies = _im_compose_external_file_issues(selected_doc)
            if dependencies:
                notes.append(f'{len(dependencies)} zusätzliche Datei-Abhängigkeit(en) erkannt. Im Konfigurationsschritt vor der Installation auflösen.')
                notes.extend(dependencies[:3])
            if any('build' in svc for svc in selected_doc['services'].values()):
                notes.append('Die gewählte Compose verwendet lokale Docker-Builds; vor der Installation ein offizielles, veröffentlichtes Image bevorzugen oder den vollständigen Build-Kontext bereitstellen.')
            elif path.lower().rsplit('/', 1)[-1] in ('docker-compose-image-tag.yml', 'docker-compose-image-tag.yaml', 'compose-image-tag.yml', 'compose-image-tag.yaml'):
                notes.append('Offizielle Image-Tag-Compose ausgewählt: Kein lokaler Docker-Build nötig. Externe env_file, Datei-Mounts und Initialisierung bleiben separate Voraussetzungen; diese nicht stillschweigend entfernen.')
        except HTTPException:
            pass
        if limited or probe_limited or content_time_limited:
            notes.append('GitHub-Suche teilweise begrenzt: Nicht alle Pfade oder YAML-Kandidaten konnten geprüft werden. Weitere Varianten können vorhanden sein.')
        else:
            notes.append('GitHub-Dateibaum vollständig erfasst. Für die Installation relevante Dateien inhaltlich geprüft; der gesamte Quellcode wurde nicht heruntergeladen.')
        head = content[:5000]
        if re.search(r'EXPERIMENTAL|EXPERIMENTELL', head[:1700], re.I):
            notes.append('Die Quell-Datei bezeichnet diese Konfiguration als experimentell.')
        if 'NEW INSTALLATIONS ONLY' in head[:1700].upper():
            notes.append('Hinweis des Herausgebers: nur für Neuinstallationen; keine bestehenden Daten übernehmen.')
        if re.search(r'\bno login yet\b|\bno authentication\b', head, re.I):
            notes.append('Sicherheitshinweis aus der Compose-Datei: Die Weboberfläche besitzt noch keinen eigenen Anmeldeschutz. Bei frei veröffentlichtem Port ist sie im LAN erreichbar. Vor der Installation Zugriff absichern.')
        if any(part in _GITHUB_EXAMPLE_DIRS for part in path.lower().split('/')[:-1]):
            notes.append('Offizielle Beispiel-Compose gefunden. Externe Netzwerke, env_file, Reverse Proxy und Secrets vor dem ZimaOS-Start prüfen; eine Datei im Beispielordner ist nicht automatisch eigenständig installierbar.')
        external = selected_doc.get('networks', {}) if isinstance(selected_doc, dict) else {}
        if isinstance(external, dict) and any(isinstance(v, dict) and v.get('external') for v in external.values()):
            notes.append('Die Hersteller-Compose verlangt bereits existierende externe Docker-Netzwerke. Diese müssen bei der Installation vorhanden sein oder der Netzwerkplan muss angepasst werden.')
        if other_valid:
            notes.append('Weitere gültige Compose-Dateien erkannt. Die Variante wurde anhand von Dateipfad und ZimaOS-Metadaten ausgewählt; für spezielle Setups die Quell-Datei prüfen.')
        elif len(candidates) > 1:
            notes.append('Es gibt weitere mögliche Installationsdateien. Die passendste wurde geprüft und gewählt; alternative Varianten bei Bedarf gesondert prüfen.')
        return content, url, notes

    _im_scan_progress('Keine passende Compose-Datei gefunden. Installationsanleitungen werden untersucht …')
    documented = _compose_from_docker_guide(owner, repo, branch, files)
    if documented is not None:
        return documented
    _im_scan_progress('Installationsskripte werden ohne Ausführung ausgewertet …')
    scripted = _github_compose_from_install_scripts(owner, repo, branch, files)
    if scripted is not None:
        return scripted
    _im_scan_progress('Offizielle Projektdokumentation wird geprüft …')
    external_docs = _compose_from_official_external_docs(
        owner, repo, branch, files,
        meta.get('homepage', '') if isinstance(meta.get('homepage'), str) else '')
    if external_docs is not None:
        return external_docs
    published_template = _publisher_template(owner, repo)
    if published_template is not None:
        return published_template
    # In a truncated/limited tree scan, absence of a Compose file is NOT
    # proof that the repository lacks one. Probe publisher raw files before
    # returning an unsupported-project diagnosis. This also covers an index
    # that omits a deployment subtree for other reasons.
    if limited:
        fallback = _discover_without_github_api(owner, repo)
        if fallback is not None:
            return fallback
    diagnostic = _diagnose_non_docker_repository(owner, repo, branch, files, limited or probe_limited or content_time_limited)
    if any(path.rsplit('/', 1)[-1].lower() == 'dockerfile' for path in files):
        diagnostic['evidence'].append('Dockerfile')
        diagnostic['explanation'] += (' Ein Dockerfile ist zwar vorhanden, aber ohne '
                                       'geeignete Build-Dateien und Konfiguration lässt sich kein sicherer ZimaOS-Start ableiten.')
    raise HTTPException(422, detail=diagnostic)


def _unresolved_runtime_variables(doc: dict) -> set[str]:
    """Only Compose runtime fields matter, never explanatory x-casaos.tips text.

    Tips, taglines, and descriptions may legitimately quote ${EXAMPLE} in prose.
    Docker will not interpolate those as Compose service configuration.
    """
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, str):
            found.update(m.group(0) for m in ENV_VAR.finditer(value))
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(doc.get('services', {}))
    walk(doc.get('networks', {}))
    walk(doc.get('volumes', {}))
    walk(doc.get('secrets', {}))
    walk(doc.get('configs', {}))
    walk(doc.get('name', ''))
    casa = doc.get('x-casaos', {})
    if isinstance(casa, dict):
        for field in ('port_map', 'hostname', 'scheme', 'index', 'icon'):
            walk(casa.get(field, ''))
    return found


def _resolve_compose_variables(content: str) -> tuple[str, list[str]]:
    """Resolve real Compose settings, including nested defaults like ${A:-${B:-}}.

    Do not apply regex substitutions to raw YAML/comments/README text: that
    would alter literal install instructions and optional CasaOS tips.
    """
    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError:
        return content, []  # The existing safe_yaml reports precise syntax errors.
    if not isinstance(doc, dict):
        return content, []

    # Only innermost ${...} matches first; a second pass handles the outer default.
    token = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:\?|\?|:-|-)([^{}]*))?\}")
    generated: dict[str, str] = {}
    defaults: set[str] = set()
    unresolved: set[str] = set()

    # This is a locally-generated HealthLog HMAC key, not a vendor API token.
    # Only recognize it for the published HealthLog image.
    healthlog_image = any(
        isinstance(svc, dict) and (
            str(svc.get('image') or '').lower() == 'ghcr.io/mbombeck/healthlog'
            or str(svc.get('image') or '').lower().startswith((
                'ghcr.io/mbombeck/healthlog:',
                'ghcr.io/mbombeck/healthlog@',
                'ghcr.io/mbombeck/healthlog$',
            ))
        ) for svc in (doc.get('services') or {}).values()
    )

    # Existing explicit upstream values always outrank generated fallbacks.
    known: dict[str, set[str]] = {}
    for service in (doc.get('services') or {}).values():
        if not isinstance(service, dict):
            continue
        for key, value in _im_environment_entries(service).items():
            if value and '${' not in value:
                known.setdefault(key, set()).add(value)
    existing = {key: next(iter(values)) for key, values in known.items()
                if len(values) == 1}

    # Only a bundled local database permits generating its user and DB name.
    local_database = any(
        isinstance(svc, dict) and re.match(
            r'^(?:(?:docker\.io|ghcr\.io)/)?(?:library/)?(?:postgres|mysql|mariadb)(?::|@|$)',
            str(svc.get('image') or '').lower())
        for svc in (doc.get('services') or {}).values()
    )
    database_names = {'POSTGRES_USER', 'POSTGRES_DB', 'MYSQL_USER',
                      'MYSQL_DATABASE', 'MARIADB_USER', 'MARIADB_DATABASE'}
    database_defaults = {'POSTGRES_DB': 'appdb', 'MYSQL_DATABASE': 'appdb',
                         'MARIADB_DATABASE': 'appdb'}

    def local_secret_name(name: str) -> bool:
        if _im_credential_spec(name, doc)['mode'] == 'external':
            return False
        standard = bool(re.search(
            r'(?:SECRET(?:_KEY)?|PASSWORD|PASSWD|TOKEN|PRIVATE_KEY|MASTER_KEY)$', name))
        return standard or (healthlog_image and name in ('API_TOKEN_HMAC_KEY', 'ENCRYPTION_KEY'))

    def expand(value: str) -> str:
        # Compose conditional + operators for optional variables. Match an
        # optional nested ${VAR} expression before expanding inner tokens.
        optional_condition = re.compile(
            r'\$\{[A-Za-z_][A-Za-z0-9_]*(?::\+|\+)(?:[^{}]|\$\{[^{}]*\})*\}')
        result = optional_condition.sub('', value)
        for _ in range(16):
            def substitute(match: re.Match) -> str:
                name, operator, fallback = match.groups()
                if name in generated:
                    return generated[name]
                if name in existing:
                    defaults.add(name)
                    return existing[name]
                if name == 'TZ':
                    zone, _ = _host_timezone()
                    if zone:
                        defaults.add(name)
                        return zone
                # Required Compose forms ${VAR:?message} / ${VAR?message}:
                # generate only credentials, never guess an existing host path.
                if operator in (':?', '?'):
                    if local_secret_name(name):
                        generated[name] = _im_generate_local_secret(name, doc)
                        return generated[name]
                    if local_database and name in database_names:
                        generated[name] = database_defaults.get(name, 'app_' + secrets.token_hex(4))
                        return generated[name]
                    unresolved.add(name)
                    return match.group(0)
                # Empty defaults mean optional/unconfigured. Don't enable optional
                # authentication/tunnel/OIDC credentials with invented secrets.
                if operator is not None and fallback == '':
                    defaults.add(name)
                    return ''
                if local_secret_name(name) and name != 'ACCESS_TOKEN_URL':
                    generated[name] = _im_generate_local_secret(name, doc)
                    return generated[name]
                if local_database and name in database_names and operator is None:
                    generated[name] = database_defaults.get(name, 'app_' + secrets.token_hex(4))
                    return generated[name]
                if operator is not None:
                    defaults.add(name)
                    return fallback or ''
                unresolved.add(name)
                return match.group(0)

            nxt = token.sub(substitute, result)
            if nxt == result:
                break
            result = nxt
        return result

    def walk(value: Any) -> Any:
        if isinstance(value, str):
            return expand(value)
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        return value

    # Do not mutate the descriptive CasaOS metadata. The x-casaos.port_map is
    # runtime-relevant and must be resolved before installation.
    for key in ('services', 'networks', 'volumes', 'secrets', 'configs', 'name'):
        if key in doc:
            doc[key] = walk(doc[key])
    casa = doc.get('x-casaos')
    if isinstance(casa, dict):
        for field in ('port_map', 'hostname', 'scheme', 'index', 'icon'):
            if field in casa:
                casa[field] = walk(casa[field])

    notes = []
    if generated:
        notes.append('Zufällig erzeugte Zugangswerte: ' + ', '.join(sorted(generated)) + '. Vor Installation prüfen und sicher aufbewahren.')
    if defaults:
        notes.append('Compose-Standardwerte eingesetzt für: ' + ', '.join(sorted(defaults)) + '.')
    unresolved = _unresolved_runtime_variables(doc)
    if unresolved:
        notes.append('Diese Variablen brauchen konkrete Werte: ' + ', '.join(sorted(unresolved)) + '.')
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False), notes


def _published_images_in_readme(project_url: str, resolved_url: str, doc: dict, suggestions: list[dict] | None = None) -> list[str]:
    """Suggest matching publisher images without changing upstream Compose.

    The user must explicitly accept an image substitution in the source editor.
    """
    if not project_url.startswith('https://github.com/'):
        return []
    sections = urllib.parse.urlsplit(project_url).path.strip('/').split('/')
    resolved = urllib.parse.urlsplit(resolved_url).path.strip('/').split('/')
    if len(sections) != 2 or len(resolved) < 3:
        return []
    owner, repo = sections
    branch = resolved[2]
    if not all(GITHUB_PART.fullmatch(s) for s in (owner, repo)):
        return []
    needs = [(name, svc) for name, svc in doc.get('services', {}).items()
             if isinstance(svc, dict) and isinstance(svc.get('image'), str)
             and '/' not in svc['image']]
    if not needs:
        return []
    try:
        url = 'https://raw.githubusercontent.com/' + '/'.join(urllib.parse.quote(s, safe='') for s in (owner, repo, branch, 'README.md'))
        text = _download_remote(url)
    except (HTTPException, OSError, ValueError):
        return []
    images = re.findall(r'^\s*image:\s*[\"\']?([A-Za-z0-9][A-Za-z0-9._/@:-]{1,240})', text, re.M)
    notes: list[str] = []
    for name, svc in needs:
        matching = [image for image in images if '/' in image and image.split('/')[-1].split(':')[0] == name]
        if len(set(matching)) != 1:
            continue
        old_image = svc['image']
        if suggestions is not None:
            suggestions.append({
                'service': name,
                'current': old_image,
                'recommended': matching[0],
                'readme_url': f'https://github.com/{owner}/{repo}/blob/{branch}/README.md',
            })
        notes.append(f'{name}: In der Hersteller-README ist {matching[0]} als veröffentlichtes Image dokumentiert. Die Originalvorlage {old_image} bleibt unverändert, bis du einen Austausch bestätigst.')
    return notes



# Generic GitLab project / public Compose discovery (no user tokens).
def _discover_gitlab_project(namespace: str) -> tuple[str, str, list[str]]:
    if not namespace or len(namespace) > 290 or not all(GITHUB_PART.fullmatch(part) for part in namespace.split('/')):
        raise HTTPException(400, 'Ungültiges öffentliches GitLab-Projekt.')
    encoded = urllib.parse.quote(namespace, safe='')
    base = 'https://gitlab.com/api/v4/projects/' + encoded
    try:
        details = json.loads(_download_remote(base, max_bytes=150000))
    except (ValueError, HTTPException) as exc:
        raise HTTPException(400, 'GitLab-Projekt nicht abrufbar. Ist es öffentlich?') from exc
    if not isinstance(details, dict) or not isinstance(details.get('default_branch'), str):
        raise HTTPException(400, 'GitLab-Projekt hat keinen erreichbaren Standardbranch.')
    branch = details['default_branch']
    if not re.fullmatch(r'[A-Za-z0-9._/-]{1,100}', branch) or '..' in branch.split('/'):
        raise HTTPException(400, 'GitLab-Branchname nicht unterstützt.')
    # First 100 files plus standard location probes. Refuse guessing dependencies.
    try:
        tree_url = base + '/repository/tree?' + urllib.parse.urlencode({'ref':branch,'recursive':'true','per_page':100})
        tree = json.loads(_download_remote(tree_url, max_bytes=150000))
        if not isinstance(tree,list): tree=[]
    except (ValueError, HTTPException):
        tree=[]
    candidates=[]
    for entry in tree:
        if isinstance(entry,dict) and entry.get('type')=='blob':
            path=str(entry.get('path') or '')
            if _safe_github_index_path(path) and _github_deploy_score(path,namespace.split('/')[-1])>=0:
                candidates.append(path)
    candidates.extend(('compose.yaml','compose.yml','docker-compose.yml','docker-compose.yaml',
                       'docker/compose.yaml','docker/docker-compose.yml','deploy/docker-compose.yml'))
    selected=sorted(set(candidates),key=lambda path:(-_github_deploy_score(path,namespace.split('/')[-1]),len(path)))[:18]
    for path in selected:
        url=('https://gitlab.com/'+namespace+'/-/raw/' + urllib.parse.quote(branch,safe='/') + '/'
             + '/'.join(urllib.parse.quote(piece,safe='') for piece in path.split('/')))
        try:
            content=_download_remote(url)
            validated,_=_resolve_compose_variables(content)
            safe_yaml(validated)
            return content,url,[f'Original-Compose aus dem öffentlichen GitLab-Projekt {namespace} gefunden: {path}.',
                               'Alle gefundenen Dienste werden übernommen; Pflichtwerte und Risiken vor Installation prüfen.']
        except (HTTPException,ValueError,yaml.YAMLError):
            continue
    raise HTTPException(422,'Keine vollständige Compose-Datei in diesem GitLab-Projekt erkannt. Bitte eine direkte Compose-URL oder YAML verwenden.')




def _codeberg_readme_compose(owner: str, repo: str, branch: str) -> tuple[str, str, list[str]] | None:
    """Use only a complete publisher-owned, image-backed Compose code fence.

    README text is documentation, not a Compose file. Extract a fenced YAML
    example without executing shell instructions or guessing Docker run flags.
    The published image must match the exact repository owner/name and is
    verified against the registry again before ZimaOS receives a POST.
    """
    allowed_images = {
        f'codeberg.org/{owner}/{repo}'.lower(),
        f'ghcr.io/{owner}/{repo}'.lower(),
        f'docker.io/{owner}/{repo}'.lower(),
        f'{owner}/{repo}'.lower(),
    }
    readmes = ('README.md', 'readme.md', 'README.MD',
               'README.markdown', 'docs/docker.md', 'docs/installation.md')
    for document_path in readmes:
        url = ('https://codeberg.org/' +
               '/'.join(urllib.parse.quote(piece, safe='') for piece in (owner, repo)) +
               '/raw/branch/' + urllib.parse.quote(branch, safe='') + '/' +
               '/'.join(urllib.parse.quote(piece, safe='') for piece in document_path.split('/')))
        try:
            markdown = _download_remote(url, max_bytes=200000)
        except HTTPException:
            continue
        if not isinstance(markdown, str):
            continue
        for match in list(_DOC_FENCE.finditer(markdown))[:45]:
            language, source = match.group(1).strip().lower(), match.group(2).strip()
            if language not in ('yaml', 'yml', 'compose', 'docker-compose', '') or len(source) > 100000:
                continue
            try:
                expanded, _ = _resolve_compose_variables(source)
                config = safe_yaml(expanded)
            except (HTTPException, ValueError, yaml.YAMLError):
                continue
            services = config['services']
            if not all(isinstance(item.get('image'), str) and not item.get('build')
                       for item in services.values()):
                continue
            # Ignore unrelated example stacks (e.g. reverse-proxy tutorials).
            # A matching publisher image is evidence; image availability
            # itself is checked later via Docker registry manifest inspection.
            refs = [str(item['image']).lower() for item in services.values()]
            identities = [ref.split('@', 1)[0].rsplit(':', 1)[0]
                          if ':' in ref.rsplit('/', 1)[-1] else ref.split('@', 1)[0]
                          for ref in refs]
            if not any(value in allowed_images for value in identities):
                continue
            config[_DOC_IMAGE_PREFLIGHT] = True
            notes = [
                f'Codeberg: Keine eigenständige Compose gefunden; vollständiges Docker-Compose-Beispiel aus {document_path} (Branch {branch}) übernommen.',
                'Das Docker-Image wird vor dem ZimaOS-Installationsauftrag über ein Registry-Manifest geprüft. '
                'Die Quell-Dokumentation ist kein Beleg für die Verfügbarkeit eines Tags.',
                'Speicherorte, Ports, Umgebungsvariablen und dokumentierte Voraussetzungen vor der Installation prüfen.',
            ]
            if re.search(r'\bno authentication or authorization\b|\bno authentication\b',
                         markdown, re.I):
                notes.append('Herstellerhinweis: Diese Anwendung bietet keine integrierte Authentifizierung. '
                             'Nur für vertrauenswürdige Netze freigeben und Fernzugriff separat absichern.')
            return yaml.safe_dump(config, allow_unicode=True, sort_keys=False), url, notes
    return None



def _discover_codeberg_project(owner: str, repo: str) -> tuple[str, str, list[str]]:
    """Find genuine Compose in a Codeberg/Forgejo project, never execute source.

    The public Forgejo API may be unavailable or rate-limited; root and common
    deployment folders are probed over its HTTPS raw endpoint as a fallback.
    Only a bounded number of YAML candidates are downloaded and parsed.
    """
    if not (GITHUB_PART.fullmatch(owner) and GITHUB_PART.fullmatch(repo)):
        raise HTTPException(400, 'Ungültiges Codeberg-Repository.')
    api = 'https://codeberg.org/api/v1/repos/' + '/'.join(
        urllib.parse.quote(piece, safe='') for piece in (owner, repo))
    branches = []
    indexed_paths: set[str] = set()
    try:
        metadata = json.loads(_download_remote(api, max_bytes=250000))
        branch = metadata.get('default_branch') if isinstance(metadata, dict) else None
        if isinstance(branch, str) and re.fullmatch(r'[A-Za-z0-9._/-]{1,120}', branch) and all(
                piece not in ('', '.', '..') for piece in branch.split('/')):
            branches.append(branch)
            try:
                tree_url = (api + '/git/trees/' + urllib.parse.quote(branch, safe='')
                            + '?recursive=true')
                tree = json.loads(_download_remote(tree_url, max_bytes=1500000))
                entries = tree.get('tree', []) if isinstance(tree, dict) else []
                if isinstance(entries, list):
                    for item in entries[:10000]:
                        if not isinstance(item, dict) or item.get('type') != 'blob':
                            continue
                        candidate = item.get('path')
                        if (isinstance(candidate, str) and _safe_github_index_path(candidate)
                                and _github_deploy_score(candidate, repo) >= 0):
                            indexed_paths.add(candidate)
            except (HTTPException, ValueError, TypeError):
                pass  # No tree index: probe known filenames, not the whole repo.
    except (HTTPException, ValueError, TypeError):
        pass
    for fallback in ('main', 'master'):
        if fallback not in branches:
            branches.append(fallback)

    filenames = ('compose.yaml', 'compose.yml', 'docker-compose.yml', 'docker-compose.yaml')
    folders = ('', 'docker/', '_docker/', 'deploy/', 'deployment/', 'install/',
               'container/', 'containers/', 'docker/compose/', 'install/docker/')
    conventional = {directory + filename for directory in folders for filename in filenames}
    ranked = sorted(indexed_paths | conventional,
                    key=lambda item: (-_github_deploy_score(item, repo), len(item), item))
    # The root Compose always receives a chance, even with many indexed YAMLs.
    ordered = list(filenames)
    ordered.extend(path for path in ranked if path not in filenames)
    # Each branch gets a bounded chance; a missing main branch must not
    # consume the entire probe budget and prevent checking master.
    max_probes_per_branch = 32
    for branch in branches:
        attempts = 0
        for filename in ordered:
            if attempts >= max_probes_per_branch:
                break
            if attempts == 4:
                documented = _codeberg_readme_compose(owner, repo, branch)
                if documented is not None:
                    return documented
            if not _safe_github_index_path(filename) or _github_deploy_score(filename, repo) < 0:
                continue
            attempts += 1
            raw = ('https://codeberg.org/' +
                   '/'.join(urllib.parse.quote(piece, safe='') for piece in (owner, repo)) +
                   '/raw/branch/' + urllib.parse.quote(branch, safe='') + '/' +
                   '/'.join(urllib.parse.quote(piece, safe='') for piece in filename.split('/')))
            try:
                source = _download_remote(raw)
                evaluated, _ = _resolve_compose_variables(source)
                compose = safe_yaml(evaluated)
            except (HTTPException, ValueError, yaml.YAMLError):
                continue
            notes = [
                f'Codeberg: Docker-Compose-Datei in {filename} gefunden (Branch {branch}).',
                'Original-YAML geprüft; Ports, Datenpfade, Zugangsdaten und Abhängigkeiten vor Installation kontrollieren.',
            ]
            if any('build' in service for service in compose['services'].values()):
                notes.append(
                    'Lokaler Docker-Build erforderlich: Codeberg-Build-Kontext wird derzeit '
                    'nicht automatisch übertragen. Ohne veröffentlichtes Image und '
                    'vollständigen Build-Kontext ist die direkte ZimaOS-Installation gesperrt.')
            return source, raw, notes
        # Fewer than four possible candidate probes, or a README check after
        # every candidate was skipped by filename validation.
        if attempts < 4:
            documented = _codeberg_readme_compose(owner, repo, branch)
            if documented is not None:
                return documented
    raise HTTPException(
        422, 'In diesem Codeberg-Projekt wurde weder eine gültige Compose-Datei '
        'noch ein überprüfbares vollständiges Compose-Beispiel in der README gefunden. '
        'Bitte eine gültige direkte Compose-YAML-Adresse oder das dokumentierte Docker-Image verwenden.')




_GITEA_PUBLIC_HOSTS = frozenset({'gitea.baerentsen.space'})


def _discover_gitea_publisher(host: str, owner: str, repo: str) -> tuple[str, str, list[str]]:
    """Read a publisher-maintained, image-backed Gitea Compose document."""
    if host not in _GITEA_PUBLIC_HOSTS or not all(GITHUB_PART.fullmatch(x) for x in (owner, repo)):
        raise HTTPException(400, 'Unzulässiger Gitea-Projektlink.')
    base = 'https://' + host + '/' + owner + '/' + repo
    branches = []
    try:
        info = json.loads(_download_remote('https://' + host + '/api/v1/repos/' + owner + '/' + repo, max_bytes=160000))
        branch = info.get('default_branch') if isinstance(info, dict) else None
        if isinstance(branch, str) and GITHUB_PART.fullmatch(branch):
            branches.append(branch)
    except (HTTPException, ValueError, TypeError):
        pass
    for fallback in ('master', 'main'):
        if fallback not in branches:
            branches.append(fallback)
    for branch in branches:
        if (owner.lower(), repo.lower()) == ('frederikbaerentsen', 'comicopds'):
            documentation = base + '/raw/branch/' + branch + '/docs/quickstart.md'
            try:
                markdown = _download_remote(documentation, max_bytes=140000)
            except HTTPException:
                markdown = ''
            for block in list(_DOC_FENCE.finditer(markdown))[:30]:
                lang, source = block.group(1).strip().lower(), block.group(2).strip()
                if lang not in ('yaml', 'yml', 'compose', 'docker-compose', ''):
                    continue
                try:
                    doc = safe_yaml(source)
                except (HTTPException, ValueError, yaml.YAMLError):
                    continue
                publisher_image = 'gitea.baerentsen.space/frederikbaerentsen/comicopds'
                matching = [svc for svc in doc['services'].values()
                            if isinstance(svc, dict)
                            and str(svc.get('image', '')).lower().split('@')[0].split(':')[0] == publisher_image
                            and not svc.get('build')]
                if len(matching) != 1 or any('build' in svc for svc in doc['services'].values()):
                    continue
                # Never silently use the example IP NAS-EXAMPLE from the README.
                matching[0].setdefault('environment', {})['SERVER_BASE'] = chr(36) + '{COMICOPDS_SERVER_BASE}'
                doc['name'] = 'comicopds'
                doc[_DOC_IMAGE_PREFLIGHT] = True
                return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), documentation, [
                    'Gitea: offizielles Compose-Beispiel in docs/quickstart.md gefunden; fertiges Hersteller-Image bevorzugt.',
                    'COMICOPDS_SERVER_BASE muss die tatsächliche NAS-Adresse enthalten, zum Beispiel http://NAS-LAN-IP:8382.',
                    'Comic-Laufwerk auswählen. Für den Internetzugriff einen Anmeldeschutz einrichten.',
                ]
        # Other projects on the approved public host can supply an image-only Compose.
        for name in ('compose.yaml', 'compose.yml', 'docker-compose.yml', 'docker-compose.yaml'):
            url = base + '/raw/branch/' + branch + '/' + name
            try:
                source = _download_remote(url)
                validated, _ = _resolve_compose_variables(source)
                doc = safe_yaml(validated)
            except (HTTPException, ValueError, yaml.YAMLError):
                continue
            if any('build' in svc for svc in doc['services'].values()):
                raise HTTPException(422, 'Gitea-Compose benötigt einen lokalen Build ohne geprüften Build-Kontext. Bitte ein veröffentlichtes Hersteller-Image verwenden.')
            return source, url, [f'Gitea: {name} im Branch {branch} erkannt.', 'Ports und NAS-Pfade vor der Installation überprüfen.']
    raise HTTPException(422, 'Kein vollständiges Hersteller-Compose-Beispiel gefunden. Bitte eine direkte Compose-YAML oder ein veröffentlichtes Docker-Image verwenden.')



_DOCKER_HUB_REPO_NAME = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,99}$')


def _dockerhub_image_from_url(value: str) -> tuple[str, str] | None:
    """Map only real Docker Hub repository pages to their image identity.

    URLs are identifiers, not HTML/Compose inputs. No browser scraping, no
    guessed image tags from filters, and no arbitrary registry hosts.
    """
    url = urllib.parse.urlsplit(value.strip())
    if not url.hostname or url.hostname.lower() != 'hub.docker.com':
        return None
    if (url.scheme != 'https' or url.username or url.password
            or url.port not in (None, 443) or url.query):
        raise HTTPException(400, 'Docker-Hub-Links müssen öffentliche HTTPS-Projektlinks ohne Zugangsdaten, Port oder Suchfilter sein.')
    segments = url.path.strip('/').split('/')
    if segments and segments[-1] == 'tags':
        segments.pop()
    if len(segments) == 3 and segments[0] == 'r':
        owner, repository = segments[1:]
        if not all(_DOCKER_HUB_REPO_NAME.fullmatch(name) and name not in ('.', '..')
                   for name in (owner, repository)):
            raise HTTPException(400, 'Ungültiger Docker-Hub-Repository-Name.')
        image = repository if owner == 'library' else owner + '/' + repository
        canonical = 'https://hub.docker.com/r/' + owner + '/' + repository
    elif len(segments) == 2 and segments[0] == '_':
        repository = segments[1]
        if not _DOCKER_HUB_REPO_NAME.fullmatch(repository) or repository in ('.', '..'):
            raise HTTPException(400, 'Ungültiger offizieller Docker-Hub-Image-Name.')
        image = repository
        canonical = 'https://hub.docker.com/_/' + repository
    else:
        raise HTTPException(400, 'Docker-Hub-Link nicht unterstützt. Bitte /r/Herausgeber/Image oder /_/Image verwenden.')
    return image + ':latest', canonical


def _dockerhub_url_safe_draft(document: dict, image: str) -> list[str]:
    """Make imported ClamAV daemon drafts private by default, no Web UI guessed."""
    name = image.lower().split('@', 1)[0].split(':', 1)[0]
    if name not in ('clamav/clamav', 'docker.io/clamav/clamav'):
        return []
    notes = [
        'ClamAV ist ein Virenscanner ohne Weboberfläche. Ein Host-Port für clamd '
        'wird nicht automatisch freigegeben; Datei-Mounts und Scan-Aufträge '
        'müssen anhand der Herstellerdokumentation eingerichtet werden.'
    ]
    for service in document['services'].values():
        ref = str(service.get('image') or '').lower()
        if ref.split('@', 1)[0].split(':', 1)[0] not in ('clamav/clamav', 'docker.io/clamav/clamav'):
            continue
        keep = []
        for mapping in service.get('ports', []) or []:
            if isinstance(mapping, str):
                without_proto = mapping.rsplit('/', 1)[0]
                target = without_proto.rsplit(':', 1)[-1]
            elif isinstance(mapping, dict):
                target = str(mapping.get('target', ''))
            else:
                keep.append(mapping)
                continue
            if target == '3310':
                notes.append('ClamAV-Port 3310/TCP wurde aus dem automatischen Host-Port-Entwurf entfernt. '
                             'Nur nach expliziter Netzwerksicherheitsprüfung manuell freigeben.')
            else:
                keep.append(mapping)
        if 'ports' in service:
            if keep:
                service['ports'] = keep
            else:
                service.pop('ports', None)
    return notes


def discover_source(value: str) -> tuple[str, str, list[str]]:
    value = value.strip()
    if len(value) > 2048:
        raise HTTPException(400, "Quell-URL ist zu lang.")
    p = urllib.parse.urlsplit(value)
    # Checking the input host before deriving the GitHub API or raw-file URL.
    _public_remote(value)
    if p.hostname and p.hostname.lower() == "github.com":
        parts = [urllib.parse.unquote(x) for x in p.path.strip("/").split("/")]
        if len(parts) >= 2 and (len(parts) == 2 or (len(parts) >= 3 and parts[2] == "releases")):
            return _discover_github_repository(parts)
        if len(parts) >= 5 and parts[2] == "blob":
            if not p.path.lower().endswith((".yml", ".yaml")):
                raise HTTPException(400, "Dieser GitHub-Dateilink ist keine Compose-YAML-Datei.")
            raw = "https://raw.githubusercontent.com/" + "/".join(urllib.parse.quote(x, safe="") for x in [parts[0], parts[1], parts[3], *parts[4:]])
            return _download_remote(raw), raw, []
        raise HTTPException(400, "Bitte einen GitHub-Repository-/Release-Link oder die direkte Compose-YAML-Datei verwenden.")
    if p.hostname and p.hostname.lower() in _GITEA_PUBLIC_HOSTS:
        parts = [urllib.parse.unquote(part) for part in p.path.strip('/').split('/')]
        if len(parts) == 2:
            return _discover_gitea_publisher(p.hostname.lower(), *parts)
        if (len(parts) >= 6 and parts[2] in ('src', 'raw') and parts[3] in ('branch', 'tag', 'commit')):
            owner, repo, _, kind, branch = parts[:5]
            pathname = '/'.join(parts[5:])
            if not (all(GITHUB_PART.fullmatch(x) for x in (owner, repo, branch))
                    and _safe_github_index_path(pathname)
                    and pathname.lower().endswith(('.yaml', '.yml'))):
                raise HTTPException(400, 'Ungültiger Gitea-Compose-Dateipfad.')
            url = 'https://' + p.hostname.lower() + '/' + owner + '/' + repo + '/raw/' + kind + '/' + branch + '/' + pathname
            source = _download_remote(url)
            validated, _ = _resolve_compose_variables(source)
            doc = safe_yaml(validated)
            if any('build' in svc for svc in doc['services'].values()):
                raise HTTPException(422, 'Gitea-Compose enthält einen lokalen Build ohne verifizierten Build-Kontext. Bitte die Hersteller-Image-Anleitung verwenden.')
            return source, url, []
        raise HTTPException(400, 'Bitte Gitea-Projektlink oder direkte Compose-YAML-Adresse verwenden.')
    if p.hostname and p.hostname.lower() == 'codeberg.org':
        parts = [urllib.parse.unquote(part) for part in p.path.strip('/').split('/')]
        if len(parts) == 2:
            return _discover_codeberg_project(*parts)
        if (len(parts) >= 6 and parts[2] in ('src', 'raw')
                and parts[3] in ('branch', 'tag', 'commit')):
            owner, repo, _, ref_kind, ref = parts[:5]
            path = parts[5:]
            if not (GITHUB_PART.fullmatch(owner) and GITHUB_PART.fullmatch(repo)
                    and GITHUB_PART.fullmatch(ref) and
                    all(_safe_github_index_path(piece) for piece in path)):
                raise HTTPException(400, 'Ungültiger Codeberg-Dateipfad.')
            if not path[-1].lower().endswith(('.yml', '.yaml')):
                raise HTTPException(400, 'Der Codeberg-Dateilink verweist nicht auf eine YAML-Datei.')
            raw = ('https://codeberg.org/' + urllib.parse.quote(owner, safe='') + '/'
                   + urllib.parse.quote(repo, safe='') + '/raw/' + ref_kind + '/'
                   + urllib.parse.quote(ref, safe='') + '/' +
                   '/'.join(urllib.parse.quote(piece, safe='') for piece in path))
            return _download_remote(raw), raw, []
        raise HTTPException(400, 'Bitte einen Codeberg-Projektlink oder eine direkte Compose-YAML-Adresse verwenden.')
    if p.hostname and p.hostname.lower() == 'gitlab.com':
        path=p.path.strip('/')
        if '/-/blob/' in path:
            prefix, suffix=path.split('/-/blob/',1)
            return discover_source('https://gitlab.com/'+prefix+'/-/raw/'+suffix)
        if '/-/raw/' in path and p.path.lower().endswith(('.yml','.yaml')):
            return _download_remote(value),value,[]
        if '/-/' not in path and len(path.split('/'))>=2:
            return _discover_gitlab_project(path)
        raise HTTPException(400,'Bitte GitLab-Projekt oder direkte Compose-Datei verwenden.')
    if not p.path.lower().endswith((".yml", ".yaml")):
        raise HTTPException(400, "Die URL verweist nicht auf eine YAML-Datei. Bitte einen Compose-Dateilink verwenden.")
    return _download_remote(value), value, []




def _matched_publisher_image(compose: dict, image: str) -> bool:
    """Confirm the selected publisher Compose really deploys this exact image.

    Never accept a random same-owner repository, README mention or Dockerfile
    as evidence. An image default in ${IMAGE:-...} is legitimate, but other
    substitutions must not be silently evaluated here.
    """
    def identity(ref: str) -> str:
        ref = ref.strip().lower()
        # Docker Hub aliases are the same publisher image, but GHCR/other
        # registries are NEVER rewritten to a similarly named Docker Hub repo.
        if ref.startswith(('docker.io/', 'index.docker.io/')):
            ref = ref.split('/', 1)[1]
        path = ref.split('@', 1)[0]
        untagged = path.rsplit(':', 1)[0] if ':' in path.rsplit('/', 1)[-1] else path
        first = untagged.split('/', 1)[0]
        if '.' not in first and ':' not in first and first != 'localhost':
            if '/' not in untagged:
                ref = 'library/' + ref
        return ref if '@' in ref or ':' in ref.rsplit('/', 1)[-1] else ref + ':latest'

    expected = identity(image.lower())
    images = [service.get('image') for service in compose.get('services', {}).values()
              if isinstance(service, dict)]
    for value in images:
        if not isinstance(value, str):
            continue
        raw = value.strip()
        if identity(raw.lower()) == expected:
            return True
        substitution = re.fullmatch(
            r'\$\{[A-Za-z_][A-Za-z0-9_]*(?::-|-)([^{}]+)\}', raw)
        if substitution and identity(substitution.group(1).lower()) == expected:
            return True
    return False


def _verified_stirling_pdf_compose(image: str) -> tuple[str, str, str, list[str]] | None:
    """Explicit publisher recipe, grounded in https://docs.stirlingpdf.com/Server/Install/Docker/.

    Never apply to unrelated image names or silently add guessed credentials.
    """
    reference = image.lower().strip()
    accepted = (
        'docker.stirlingpdf.com/stirlingtools/stirling-pdf:latest',
        'stirlingtools/stirling-pdf:latest',
        'ghcr.io/stirling-tools/stirling-pdf:latest',
    )
    if reference not in accepted:
        return None
    mounts = {
        'configs': '/configs',
        'logs': '/logs',
        'customFiles': '/customFiles',
        'pipeline': '/pipeline',
        'storage': '/storage',
        'tessdata': '/usr/share/tessdata',
    }
    service = {
        'image': image,
        'ports': ['8080:8080'],
        'volumes': [f'/DATA/AppData/stirling-pdf/{name}:{target}' for name, target in mounts.items()],
        'mem_limit': '4g',
        'restart': 'unless-stopped',
    }
    doc = {'name': 'stirling-pdf', 'services': {'stirling-pdf': service}}
    return (
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        'https://docs.stirlingpdf.com/Server/Install/Docker/',
        'https://github.com/Stirling-Tools/Stirling-PDF',
        ['Offizielle Stirling-PDF-Docker-Vorlage: 8080/tcp, sechs Speicherordner, 4 GB RAM.',
         'Host-Port 8080 vor Installation prüfen und bei Belegung im Compose ändern.',
         'Herstellerdokumentation und Standard-Anmeldedaten vor öffentlicher Freigabe prüfen.'],
    )


def _publisher_compose_for_image(image: str) -> tuple[str, str, str, list[str]] | None:
    """Find the *publisher's verified deployment* for a GHCR/Docker Hub image.

    Query only a few same-namespace GitHub repositories. No registry layers
    are downloaded and no Docker commands executed. A candidate is trusted
    only if a parsed Compose actually uses the exact requested image/tag.
    We prefer the official `-docker` repository, then same-name repositories.
    """
    ref = image.split('@', 1)[0]
    without_tag = ref.rsplit(':', 1)[0] if ':' in ref.rsplit('/', 1)[-1] else ref
    parts = without_tag.split('/')
    if len(parts) == 3 and parts[0].lower() == 'ghcr.io':
        owner, package = parts[1:]
    elif len(parts) == 2 and '.' not in parts[0] and ':' not in parts[0]:
        owner, package = parts
    elif len(parts) == 3 and parts[0].lower() in ('docker.io', 'index.docker.io'):
        owner, package = parts[1:]
    else:
        return None
    if not GITHUB_PART.fullmatch(owner) or not GITHUB_PART.fullmatch(package):
        return None

    # Exact publisher namespace and image reference only. Never infer ports or
    # volumes from a coincidental package name in a different namespace.
    if (owner.lower() == 'gtsteffaniak' and package.lower() == 'filebrowser'
            and without_tag.lower() == 'ghcr.io/gtsteffaniak/filebrowser'
            and image.rsplit(':', 1)[-1].lower() == 'stable'):
        content, url, notes = _filebrowser_publisher_draft()
        return content, url, 'https://github.com/gtsteffaniak/filebrowser', notes
    repositories = list(dict.fromkeys((package + '-docker', package, 'docker-' + package)))
    for repo in repositories:
        if not GITHUB_PART.fullmatch(repo):
            continue
        try:
            original, url, discovery_notes = _discover_github_repository([owner, repo])
        except HTTPException as exc:
            # Missing repositories and verified non-Docker repositories are
            # negative candidates. All network/auth/API failures must remain
            # visible instead of becoming a misleading minimal Compose.
            reason = str(exc.detail)
            if exc.status_code == 422 or (exc.status_code == 400 and 'HTTP 404' in reason):
                continue
            raise
        try:
            raw_document = yaml.safe_load(original)
            if not isinstance(raw_document, dict) or not isinstance(raw_document.get('services'), dict):
                continue
            if not _matched_publisher_image(raw_document, image):
                continue
            # safe_yaml expects concrete image references, so resolve a
            # temporary copy for validation. The template kept for the actual
            # wizard is still untouched and gets its own random secrets later.
            validate_source, _ = _resolve_compose_variables(original)
            safe_yaml(validate_source)
            document = raw_document
        except (HTTPException, yaml.YAMLError, ValueError):
            continue
        # The exact image reference is proven in the manufacturer's Compose.
        # Mark it for registry-manifest preflight, so GHCR-private packages do
        # not create broken ZimaOS dashboard tiles.
        document[_DOC_IMAGE_PREFLIGHT] = True
        content = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, default_flow_style=False)
        project = f'https://github.com/{owner}/{repo}'
        notes = [f'Passende Herausgeber-Compose für {image} gefunden: {url}.',
                 'Dienste, Datenbank, Ports, Umgebungsvariablen und Volumes aus der verifizierten Originalvorlage übernommen. '
                 'Noch offene Pflichtwerte (z. B. SITE_URL) müssen vor dem Installieren bestätigt werden.',
                 'Die Images werden vor dem ZimaOS-Installationsauftrag auf Registry-Zugriff geprüft; '
                 'private oder fehlende Images erzeugen keine defekte Dashboard-Kachel.']
        notes.extend(discovery_notes)
        return content, url, project, notes
    return None



# General-purpose publisher Docker Hub documentation discovery. Exact image
# matching is essential: descriptions are untrusted project-supplied data.
_DOCKER_HUB_DOC_FENCE = re.compile(r'```[^\n`]*\n(.*?)\n```', re.S)


def _dockerhub_repository_parts(image: str) -> tuple[str, str] | None:
    value = image.strip().split('@', 1)[0]
    head = value.split('/', 1)[0].lower()
    if head in ('docker.io', 'index.docker.io', 'registry-1.docker.io'):
        value = value.split('/', 1)[1]
    elif head == 'ghcr.io' or '.' in head or (':' in head and '/' in value):
        return None
    if ':' in value.rsplit('/', 1)[-1]:
        value = value.rsplit(':', 1)[0]
    pieces = value.split('/')
    if len(pieces) == 1:
        pieces.insert(0, 'library')
    if len(pieces) != 2 or not all(re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', t) for t in pieces):
        return None
    return pieces[0], pieces[1]


def _dockerhub_publisher_documentation(image: str) -> tuple[str, str, str, list[str]] | None:
    """Find exactly matching Compose in publisher-maintained Docker Hub description.

    Read only text from the registry owner. Never execute, render remote HTML,
    infer credentials, or trust a template for a different image/tag.
    """
    parts = _dockerhub_repository_parts(image)
    if not parts:
        return None
    owner, repo = parts
    url = f'https://hub.docker.com/v2/repositories/{owner}/{repo}/'
    try:
        request = urllib.request.Request(url, headers={'Accept': 'application/json',
                                                        'User-Agent': 'InstallMonitor/0.2'})
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=8) as response:
            if response.status != 200 or response.geturl() != url:
                return None
            raw = response.read(220001)
        if len(raw) > 220000:
            return None
        details = json.loads(raw)
    except (ValueError, OSError, urllib.error.HTTPError):
        return None
    desc = details.get('full_description') if isinstance(details, dict) else None
    if not isinstance(desc, str) or len(desc) > 180000:
        return None
    # Both Markdown and Docker Hub details belong to the verified publisher;
    # a separate GitHub repository with a similar name is not proof.
    for block in _DOCKER_HUB_DOC_FENCE.findall(desc)[:35]:
        if len(block) > 65000:
            continue
        try:
            document = safe_yaml(block)
        except (HTTPException, yaml.YAMLError, ValueError, TypeError):
            continue
        if _matched_publisher_image(document, image):
            document[_DOC_IMAGE_PREFLIGHT] = True
            return (yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
                    url, 'https://hub.docker.com/r/' + owner + '/' + repo,
                    [f'Hersteller-Compose in der Docker-Hub-Beschreibung für {image} gefunden.',
                     'Veröffentlichte Vorlage wird vor der Installation geprüft; erforderliche Werte bestätigen.'])
    for block in _DOCKER_HUB_DOC_FENCE.findall(desc)[:35]:
        document = _compose_from_documented_run(block, repo)
        if document and _matched_publisher_image(document, image):
            document[_DOC_IMAGE_PREFLIGHT] = True
            return (yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
                    url, 'https://hub.docker.com/r/' + owner + '/' + repo,
                    ['Docker-Run-Beispiel des Herausgebers in Compose übertragen; alle Argumente überprüft.',
                     'Fehlende Abhängigkeiten und Zugangsdaten vor der Installation prüfen.'])
    return None


def _auto_reassign_conflicting_ports(document: dict) -> list[str]:
    """Read-only conflict check; replace only *host* ports with tested free ports.

    Fail conservatively when Docker socket/probe is unavailable: never invent
    a free port. The draft remains editable and the existing preflight blocks.
    """
    notes = []
    try:
        result = port_report(document)
    except HTTPException as exc:
        notes.append('NAS-Portprüfung nicht möglich: ' + str(exc.detail))
        return notes
    for item in result.get('ports', []):
        if item.get('available') or not item.get('suggestion') or item.get('host_network'):
            continue
        svc = item['service']
        old_port, new_port = item['host_port'], item['suggestion']
        try:
            updated = replace_port(document, svc, item['index'], new_port)
            document.clear()
            document.update(safe_yaml(updated))
            notes.append(f'{svc}: Host-Port {old_port} belegt; geprüfter freier Host-Port {new_port} vorgeschlagen. Container-Port unverändert.')
        except HTTPException:
            notes.append(f'{svc}: Port {old_port} belegt. Automatischer Ersatz nicht möglich; bitte manuell ändern.')
    return notes


def fetch_source(value: str) -> str:
    # Kept for backward compatibility and simple direct calls.
    return discover_source(value)[0]


# Port checks: running Docker containers and, when available, local NAS listeners.
# Host sockets MUST be probed in the NAS network namespace, not in this app's
# Docker bridge namespace. The tiny helper is run from the already local image
# using --network host, read-only FS, no mounts or added capabilities.
def _declared_host_network_port(doc: dict, service: str) -> int | None:
    """Resolve a documented WebUI port for the correct host-network service.

    Prefer explicit x-casaos metadata for the matching main service.  A small
    publisher-verified exception covers LAN Orangutan: its official Compose
    declares ORANGUTAN_PORT and uses host networking. Do not infer ports from
    arbitrary environment variables or unrelated services.
    """
    services = doc.get('services')
    if not isinstance(services, dict) or service not in services:
        return None
    config = services[service]
    if not isinstance(config, dict) or config.get('network_mode') != 'host':
        return None
    casa = doc.get('x-casaos')
    if isinstance(casa, dict):
        main = casa.get('main')
        # A single-service upstream document can omit x-casaos.main.
        if main == service or (main is None and len(services) == 1):
            value = casa.get('port_map')
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                port = str(value).strip()
                if re.fullmatch(r'[0-9]{1,5}', port) and 1 <= int(port) <= 65535:
                    return int(port)
    image = str(config.get('image') or '').lower()
    if (image.startswith('ghcr.io/291-group/lan-orangutan:')
            or image == 'ghcr.io/291-group/lan-orangutan'
            or image.startswith('291group/lan-orangutan:')
            or image == '291group/lan-orangutan'):
        # Publisher source: github.com/291-Group/LAN-Orangutan/docker-compose.yml
        # The documented default is 291. Use only the actual declared value:
        # custom ports remain supported without guessing or mutating Compose.
        raw = _get_service_environment(config, 'ORANGUTAN_PORT').strip()
        if re.fullmatch(r'[0-9]{1,5}', raw) and 1 <= int(raw) <= 65535:
            return int(raw)
    # NetAlertX official host-network Compose declares both web and GraphQL
    # ports through environment values. Do not infer arbitrary PORT variables
    # for other images; these defaults are publisher-specific.
    if _is_netalertx_image(image):
        return _netalertx_declared_port(config, 'PORT')
    return None



def _is_netalertx_image(image: str) -> bool:
    return image.split('@', 1)[0].split(':', 1)[0].lower() == 'ghcr.io/netalertx/netalertx'


def _netalertx_declared_port(config: dict, key: str) -> int | None:
    """Read a concrete official NetAlertX PORT/GRAPHQL_PORT declaration.

    Compose interpolation like ${PORT:-20211} has a literal default.
    A variable with no default cannot safely be guessed.
    """
    raw = _get_service_environment(config, key).strip()
    match = re.fullmatch(r'\$\{' + re.escape(key) + r':?-(\d{1,5})\}', raw)
    if match:
        raw = match.group(1)
    if re.fullmatch(r'\d{1,5}', raw) and 1 <= int(raw) <= 65535:
        return int(raw)
    return None


def _bindings(doc: dict) -> list[dict]:
    items: list[dict] = []
    for service, config in doc["services"].items():
        raw_ports = config.get("ports", []) or []
        if config.get("network_mode") == "host":
            if raw_ports:
                raise HTTPException(400, f"{service}: Bei network_mode: host darf Compose keine ports:-Weiterleitungen enthalten.")
            # Host networking has no Compose port mapping. Use only a WebUI port
            # declared in the matching ZimaOS x-casaos metadata. Host mode can
            # open further ports: do NOT claim to have checked all of them.
            # Never offer automatic remapping of a host-network port.
            declared_port = _declared_host_network_port(doc, service)
            if declared_port is None:
                image = str(config.get("image", "")).lower()
                if image.startswith("ghcr.io/music-assistant/server:") or image == "ghcr.io/music-assistant/server":
                    declared_port = 8095  # verified official default WebUI port
            if declared_port is None:
                raise HTTPException(400, f"{service}: network_mode: host ohne eindeutig dokumentierten Web-Port. Für diesen Dienst konnte weder x-casaos.port_map noch eine unterstützte Hersteller-Portangabe zugeordnet werden; bitte die Hersteller-Compose ergänzen.")
            items.append({"service": service, "index": -1, "host_port": declared_port,
                          "target_port": declared_port, "protocol": "tcp", "host_ip": "",
                          "host_network": True})
            if _is_netalertx_image(str(config.get('image') or '')):
                graphql_port = _netalertx_declared_port(config, 'GRAPHQL_PORT')
                if graphql_port is None:
                    raise HTTPException(400, f"{service}: NetAlertX GRAPHQL_PORT ist nicht eindeutig aufgelöst. Bitte einen konkreten Port oder einen Compose-Default angeben.")
                if graphql_port == declared_port:
                    raise HTTPException(400, f"{service}: NetAlertX PORT und GRAPHQL_PORT dürfen nicht identisch sein.")
                items.append({"service": service, "index": -2, "host_port": graphql_port,
                              "target_port": graphql_port, "protocol": "tcp", "host_ip": "",
                              "host_network": True})
            continue
        if not isinstance(raw_ports, list):
            raise HTTPException(400, f"{service}: 'ports' muss eine Liste sein.")
        for index, value in enumerate(raw_ports):
            proto, host, target, host_ip = "tcp", None, None, ""
            if isinstance(value, dict):
                proto = str(value.get("protocol") or "tcp").lower()
                host = value.get("published")
                target = value.get("target")
                host_ip = str(value.get("host_ip") or "")
                if host is None: continue  # Docker chooses an ephemeral host port.
                if not str(host).isdigit() or not str(target).isdigit():
                    raise HTTPException(400, f"{service}: dynamische Portbereiche bitte manuell prüfen.")
            elif isinstance(value, (str, int)):
                port_text = str(value)
                if "/" in port_text:
                    port_text, proto = port_text.rsplit("/", 1)
                parts = port_text.rsplit(":", 2)
                if len(parts) < 2:
                    if port_text.isdigit(): continue  # container-only; Docker chooses host port
                    raise HTTPException(400, f"{service}: Portangabe '{value}' konnte nicht geprüft werden.")
                host, target = parts[-2:]
                if len(parts) == 3: host_ip = parts[0].strip("[]")
                if not host.isdigit() or not target.isdigit():
                    raise HTTPException(400, f"{service}: Portbereiche bitte als einzelne Host-Ports konfigurieren.")
            else:
                raise HTTPException(400, f"{service}: unbekanntes Portformat.")
            if proto not in ("tcp", "udp") or not (1 <= int(host) <= 65535) or not (1 <= int(target) <= 65535):
                raise HTTPException(400, f"{service}: ungültige Host-/Container-Portangabe.")
            items.append({"service": service, "index": index, "host_port": int(host),
                          "target_port": int(target), "protocol": proto, "host_ip": host_ip})
    return items


def _docker_ports() -> list[dict]:
    try:
        process = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=8, check=True)
        ids = process.stdout.split()
        if not ids: return []
        process = subprocess.run(["docker", "inspect", *ids[:250]], capture_output=True, text=True, timeout=12, check=True)
        entries = json.loads(process.stdout)
        seen = []
        for c in entries:
            name = str(c.get("Name", "")).lstrip("/")
            for key, bindings in (c.get("NetworkSettings", {}).get("Ports") or {}).items():
                protocol = key.rsplit("/", 1)[-1]
                if protocol not in ("tcp", "udp"): continue
                for binding in bindings or []:
                    port = binding.get("HostPort", "")
                    if str(port).isdigit():
                        seen.append({"host_port": int(port), "protocol": protocol,
                                     "host_ip": str(binding.get("HostIp", "")), "owner": name})
        return seen
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as exc:
        raise HTTPException(503, "Docker-Portbelegung kann nicht geprüft werden. Installation vorsichtshalber gesperrt.") from exc


_HOST_PORT_PROBE = r"""import errno, json, socket, sys
out={}
for port, proto in json.loads(sys.argv[1]):
    states=[]
    errors=[]
    for family, address in ((socket.AF_INET,'0.0.0.0'), (socket.AF_INET6,'::')):
        try:
            s=socket.socket(family, socket.SOCK_STREAM if proto=='tcp' else socket.SOCK_DGRAM)
        except OSError as e:
            if e.errno not in (errno.EAFNOSUPPORT, errno.EPROTONOSUPPORT, errno.EADDRNOTAVAIL):
                errors.append('socket '+str(e.errno)+': '+str(e.strerror))
            continue
        try:
            if family == socket.AF_INET6:
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            s.bind((address, port))
            states.append('free')
        except OSError as e:
            if e.errno == errno.EADDRINUSE:
                states.append('occupied')
            elif e.errno not in (errno.EAFNOSUPPORT, errno.EPROTONOSUPPORT, errno.EADDRNOTAVAIL):
                # EPERM/EACCES or a different socket error does not prove a conflict.
                errors.append('bind '+str(e.errno)+': '+str(e.strerror))
        finally:
            s.close()
    key=str(port)+'/'+proto
    if 'occupied' in states:
        out[key]={'status':'occupied'}
    elif errors:
        out[key]={'status':'error','detail':'; '.join(errors)[:240]}
    elif 'free' in states:
        out[key]={'status':'free'}
    else:
        out[key]={'status':'error','detail':'Keine verwendbare IP-Adressfamilie'}
print(json.dumps(out))"""


def _host_port_probe(ports: list[tuple[int, str]]) -> dict[str, dict] | None:
    if not ports: return {}
    try:
        p = subprocess.run(["docker", "inspect", "-f", "{{.Image}}", "install-monitor"],
                           capture_output=True, text=True, timeout=5, check=True)
        image = p.stdout.strip()
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image): return None
        # Ports below 1024 (for example LAN Orangutan 291) need NET_BIND_SERVICE
        # on NAS hosts with net.ipv4.ip_unprivileged_port_start=1024. Grant only
        # this capability to the short-lived, host-network bind probe.
        command = ["docker", "run", "--rm", "--network", "host", "--read-only",
                   "--user", "0:0", "--cap-drop", "ALL", "--cap-add", "NET_BIND_SERVICE",
                   "--security-opt", "no-new-privileges:true",
                   "--entrypoint", "python", image, "-c", _HOST_PORT_PROBE, json.dumps(ports)]
        probe = subprocess.run(command, capture_output=True, text=True, timeout=18, check=True)
        result = json.loads(probe.stdout)
        if not isinstance(result, dict) or not all(isinstance(v, dict) and v.get('status') in ('free','occupied','error') for v in result.values()):
            return None
        return result
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return None


def port_report(doc: dict) -> dict:
    wanted = _bindings(doc)
    if not wanted: return {"ports": [], "blocked": False, "message": "Keine festen Host-Ports definiert."}
    active = _docker_ports()
    probe_keys = {(item["host_port"], item["protocol"]) for item in wanted}
    # Probe nearby candidates once; do not guess a free port.
    for item in wanted:
        if item.get('host_network'):
            continue  # Host networking has no Docker port remapping.
        start = max(1024, item["host_port"] + 1)
        for alt in range(start, min(65536, start + 25)):
            if alt not in RESERVED: probe_keys.add((alt, item["protocol"]))
    probe = _host_port_probe(sorted(probe_keys))
    if probe is None:
        raise HTTPException(503, "NAS-Hostports konnten nicht geprüft werden. Bitte Docker-Berechtigungen bzw. Logs prüfen.")
    # An unavailable probe is not evidence of an occupied port. Keep the
    # installation blocked until verified, but report the actual check error.
    for port, proto in sorted(probe_keys):
        key = f"{port}/{proto}"
        status = probe.get(key)
        if not isinstance(status, dict) or status.get('status') not in ('free', 'occupied', 'error'):
            raise HTTPException(503, f"NAS-Portprüfung für {key} hat kein gültiges Ergebnis geliefert.")
        if status['status'] == 'error':
            detail = str(status.get('detail') or 'Unbekannter Socketfehler')[:240]
            raise HTTPException(503, f"NAS-Port {key} konnte nicht sicher geprüft werden: {detail}. Dies ist keine bestätigte Portbelegung; die Installation bleibt aus Sicherheitsgründen gesperrt.")
    claimed: dict[tuple[int,str], str] = {}
    results=[]
    for item in wanted:
        port, proto = item["host_port"], item["protocol"]
        key = (port, proto)
        owner = next((x["owner"] for x in active if x["host_port"] == port and x["protocol"] == proto), "")
        if port in RESERVED:
            reason = "reservierter ZimaOS-/Monitor-Port"
        elif owner:
            reason = f"Docker: {owner}"
        elif claimed.get(key):
            reason = f"mehrfach im Installationsplan (Dienst {claimed[key]})"
        elif probe[f"{port}/{proto}"]['status'] == 'occupied':
            reason = "NAS-Dienst/anderer Prozess belegt den Port"
        else:
            reason = ""
        claimed[key] = item["service"]
        suggestion = None
        if reason and not item.get('host_network'):
            for offset in range(25):
                alt = max(1024, port + 1) + offset
                if alt < 1024 or alt > 65535 or alt in RESERVED or (alt, proto) in claimed:
                    continue
                if probe.get(f"{alt}/{proto}", {}).get('status') != 'free': continue
                if any(x["host_port"] == alt and x["protocol"] == proto for x in active): continue
                if any(x["host_port"] == alt and x["protocol"] == proto for x in wanted): continue
                suggestion = alt
                break
        code = "reserved" if port in RESERVED else ("docker" if owner else ("duplicate" if claimed.get(key) != item["service"] and reason else ("host" if reason else "free")))
        # Exact reason-code is used for translations; reason remains human-readable.
        if reason.startswith("mehrfach"):
            code = "duplicate"
        results.append({**item, "available": not bool(reason), "reason": reason,
                        "reason_code": code, "owner": owner, "suggestion": suggestion})
    return {"ports": results, "blocked": any(not p["available"] for p in results),
            "message": "Port-Konflikte gefunden." if any(not p["available"] for p in results) else "Alle festen Host-Ports sind frei."}


def _reject_existing_named_containers(doc: dict) -> None:
    """Never reuse an explicit container_name owned by an existing installation.

    Include stopped containers: Docker/ZimaOS can still consider those names
    occupied even when there are no listening host ports to discover.
    """
    declared = set()
    for svc in doc.get('services', {}).values():
        if isinstance(svc, dict):
            name = svc.get('container_name')
            if isinstance(name, str) and name.strip():
                declared.add(name.strip())
    if not declared:
        return
    try:
        result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.Names}}'],
                                capture_output=True, text=True, timeout=10, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(503, 'Vorhandene Container konnten nicht geprüft werden. Installation vorsichtshalber gesperrt.') from exc
    occupied = sorted(declared.intersection(result.stdout.splitlines()))
    if occupied:
        raise HTTPException(409, 'Bereits vorhandener Docker-Container: ' + ', '.join(occupied) +
                            '. Die App ist bereits installiert oder als gestoppter Container vorhanden. Keine zweite Installation starten.')


def require_ports_free(doc: dict) -> dict:
    _reject_existing_named_containers(doc)
    report = port_report(doc)
    if report["blocked"]:
        details = "; ".join(f"{p['host_port']}/{p['protocol']}: {p['reason']}" for p in report["ports"] if not p["available"])
        if any(p.get('host_network') and not p['available'] for p in report['ports']):
            raise HTTPException(409, "Host-Netzwerk-Port belegt: " + details + ". Bei network_mode: host gibt es keine automatische Portumleitung. Prüfe, ob der betroffene Dienst bereits auf dem NAS läuft oder den Port nutzt.")
        raise HTTPException(409, "Host-Port bereits belegt: " + details + ". Bitte den Host-Port im Install Monitor ändern.")
    return report


def replace_port(doc: dict, service: str, index: int, new_port: int) -> str:
    chosen = next((b for b in _bindings(doc) if b["service"] == service and b["index"] == index), None)
    if not chosen: raise HTTPException(400, "Dieser Host-Port existiert nicht mehr in der Compose-Datei.")
    entry = doc["services"][service]["ports"][index]
    if isinstance(entry, dict):
        entry["published"] = str(new_port)
    else:
        old = str(entry)
        suffix = ""
        if "/" in old:
            old, proto = old.rsplit("/", 1)
            suffix = "/" + proto
        pieces = old.rsplit(":", 2)
        pieces[-2] = str(new_port)
        doc["services"][service]["ports"][index] = ":".join(pieces) + suffix
    # Update explicitly named external/published port variables for the same
    # service. Never change PORT itself: that commonly controls the internal port.
    env = doc["services"][service].get("environment", []) or []
    external = {"EXTERNAL_PORT", "WEBUI_PORT", "HOST_PORT", "PUBLIC_PORT"}
    old_port = str(chosen["host_port"])
    if isinstance(env, list):
        for i, item in enumerate(env):
            if not isinstance(item, str) or "=" not in item:
                continue
            key, value = item.split("=", 1)
            if key in external and value == old_port:
                env[i] = key + "=" + str(new_port)
    elif isinstance(env, dict):
        for key in external:
            if key in env and str(env[key]) == old_port:
                env[key] = str(new_port)
    if isinstance(doc.get("x-casaos"), dict) and doc["x-casaos"].get("main") == service:
        doc["x-casaos"]["port_map"] = str(new_port)
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)


# v0.2.19: distinguish a directory mount from a repository-shipped file.
# Importing a Compose YAML does NOT import its neighboring nginx.conf,
# Caddyfile, .env, certificates, or extra Compose fragments into ZimaOS.
_IM_FILE_SUFFIXES = frozenset({
    '.yaml', '.yml', '.json', '.conf', '.cfg', '.ini', '.toml', '.xml',
    '.properties', '.php', '.sh', '.pem', '.crt', '.key', '.cert',
    '.htpasswd', '.sql', '.js', '.ts', '.py', '.txt', '.env',
})
_IM_FILE_BASENAMES = frozenset({
    'caddyfile', 'dockerfile', 'containerfile', '.env', '.htpasswd',
    'authorized_keys', 'nginx.conf', 'traefik.yml', 'traefik.yaml',
})


def _im_file_mount_expected(source: str, target: str) -> bool:
    """Conservative heuristic: false negatives are safer than fake file creation.

    Dot-directories such as .config and .ssh must never be interpreted as
    files from the leading dot alone. The source/target must look file-like.
    """
    if not isinstance(source, str) or not isinstance(target, str):
        return False
    def looks_file(path: str) -> bool:
        name = path.rstrip('/').rsplit('/', 1)[-1].lower()
        if name in _IM_FILE_BASENAMES:
            return True
        return any(name.endswith(suffix) for suffix in _IM_FILE_SUFFIXES)
    return looks_file(source) or looks_file(target)


# v0.2.44: Docker's short volume syntax silently creates MISSING host sources
# as DIRECTORIES. This is fatal when the container target expects a config file.
# Probe only approved NAS paths and only stat their host-side basename; never
# infer that /DATA/AppData/*.yml exists merely because its parent was created.
_IM_MOUNT_FILE_PROBE = r"""
import json, os, stat
p='/im-file-check/'+os.environ['IM_FILE_BASENAME']
try:
    info=os.lstat(p)
except FileNotFoundError:
    print(json.dumps({'status':'missing'}))
except (OSError, ValueError):
    print(json.dumps({'status':'unverifiable'}))
else:
    status='regular' if stat.S_ISREG(info.st_mode) else ('directory' if stat.S_ISDIR(info.st_mode) else 'other')
    print(json.dumps({'status':status}))
"""


def _im_absolute_file_binds(doc: dict) -> list[tuple[str, str]]:
    paths = []
    for name, service in doc.get('services', {}).items():
        if not isinstance(service, dict) or service.get('profiles'):
            continue
        for mount in service.get('volumes') or []:
            if isinstance(mount, str):
                pieces = mount.split(':', 2)
                if len(pieces) < 2: continue
                source, dest = pieces[:2]
            elif isinstance(mount, dict) and mount.get('type') == 'bind':
                source, dest = mount.get('source'), mount.get('target')
            else:
                continue
            if isinstance(source, str) and isinstance(dest, str) and _im_file_mount_expected(source, dest):
                if source.startswith(('/DATA/', '/media/')) and not _im_example_host_path(source):
                    paths.append((name, source))
    return paths


def _im_host_file_mount_issues(doc: dict) -> list[str]:
    """Fail closed for file binds if NAS file type is wrong or cannot be proved.

    The disposable probe reuses ONLY our running install-monitor image, with no
    network, readonly root and readonly parent folder. `--mount` (not `-v`)
    cannot create a missing parent. No host file content is ever read or copied.
    """
    bindings = _im_absolute_file_binds(doc)
    if not bindings: return []
    if len(bindings) > 25:
        return ['Mehr als 25 Datei-Mounts: Host-Dateien bitte vor der Installation einzeln verifizieren.']
    errors: list[str] = []
    image = None
    for service, source in bindings:
        # Reject ambiguous Docker --mount option strings and parent traversals.
        if (len(source) > 500 or not re.fullmatch(r'/[A-Za-z0-9_./ -]+', source)
                or any(part in ('.', '..') for part in source.split('/'))):
            errors.append(f'{service}: Datei-Mount {source[:180]} hat einen nicht prüfbaren NAS-Pfad.')
            continue
        root = next((r for r in _BROWSE_ROOTS if source.startswith(r + '/')), None)
        physical_root = _BROWSE_MOUNT / str(root or '').lstrip('/')
        status = None
        if root and physical_root.is_dir() and not physical_root.is_symlink():
            try:
                actual = _BROWSE_MOUNT / source.lstrip('/')
                info = actual.lstat()
                status = 'regular' if stat.S_ISREG(info.st_mode) else ('directory' if stat.S_ISDIR(info.st_mode) else 'other')
            except FileNotFoundError:
                status = 'missing'
            except OSError:
                status = 'unverifiable'
        else:
            if image is None:
                try:
                    p = subprocess.run(['docker', 'inspect', 'install-monitor', '--format', '{{.Image}}'],
                                       capture_output=True, text=True, timeout=8, check=True)
                    image = p.stdout.strip() if re.fullmatch(r'sha256:[0-9a-f]{64}', p.stdout.strip()) else ''
                except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    image = ''
            if image:
                parent, filename = os.path.split(source)
                command = ['docker', 'run', '--rm', '--pull', 'never', '--network', 'none',
                           '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                           '--pids-limit', '32', '--memory', '64m',
                           '--mount', f'type=bind,source={parent},target=/im-file-check,readonly',
                           '--env', 'IM_FILE_BASENAME=' + filename,
                           '--entrypoint', 'python', image, '-c', _IM_MOUNT_FILE_PROBE]
                try:
                    p = subprocess.run(command, capture_output=True, text=True, timeout=18)
                    if p.returncode == 0:
                        outcome = json.loads(p.stdout)
                        status = outcome.get('status') if isinstance(outcome, dict) else None
                except (OSError, subprocess.TimeoutExpired, ValueError):
                    pass
        if status == 'regular':
            continue
        # Only a known PHP uploads.ini template may be provisioned during
        # the isolated preparation phase; the helper refuses existing links,
        # directories or unexpected files instead of replacing them.
        name = slug(str(doc.get('name') or next(iter(doc['services']))))
        if source in _im_wordpress_ini_templates(doc, name) and status in ('missing', None):
            continue
        if status == 'missing':
            problem = 'existiert nicht'
        elif status == 'directory':
            problem = 'ist ein Verzeichnis statt einer Datei'
        elif status == 'other':
            problem = 'ist keine reguläre Datei (möglicherweise ein Link oder Spezialdatei)'
        else:
            problem = 'konnte auf dem NAS nicht als reguläre Datei bestätigt werden'
        errors.append(f'{service}: Datei-Mount {source} {problem}. '
                      'Bitte eine echte Konfigurationsdatei unter diesem Pfad erstellen bzw. auswählen. '
                      'Die Installation bleibt gesperrt, damit Docker nicht automatisch ein Verzeichnis erzeugt.')
    return errors


def _im_compose_external_file_issues(data: dict) -> list[str]:
    """Report dependencies lost when only the YAML is sent to ZimaOS.

    No automatic remote scripts, config secrets, or file creation. A manual
    absolute host file can be used after the operator has created it.
    """
    messages = []
    included = data.get('include')
    if included:
        messages.append('Compose include: Weitere Compose-Dateien werden beim Import nicht übertragen. Bitte eine vollständig zusammengeführte Hersteller-Compose verwenden.')
    for category in ('configs', 'secrets'):
        items = data.get(category, {})
        if not isinstance(items, dict):
            continue
        for item_name, item in items.items():
            if isinstance(item, dict) and isinstance(item.get('file'), str):
                source = item['file'].strip()
                if not source.startswith('/'):
                    messages.append(f'{category}.{item_name}: Externe Datei {source} wird nicht mit dem Compose übertragen. Bitte den NAS-Dateipfad bereitstellen.')
    for service_name, service in data.get('services', {}).items():
        if not isinstance(service, dict):
            continue
        ext = service.get('extends')
        if ext:
            if isinstance(ext, dict) and ext.get('file'):
                messages.append(f'{service_name}: extends benötigt die zusätzliche Compose-Datei {ext["file"]}; diese wird nicht übertragen.')
            else:
                messages.append(f'{service_name}: extends muss vor der ZimaOS-Installation in eine vollständige Compose aufgelöst werden.')
        env = service.get('env_file')
        if env:
            entries = [env] if isinstance(env, (str, dict)) else env
            if isinstance(entries, list):
                for entry in entries:
                    name = entry if isinstance(entry, str) else entry.get('path', '') if isinstance(entry, dict) else ''
                    if isinstance(name, str) and name and not name.startswith('/'):
                        messages.append(f'{service_name}: env_file {name} wird nicht übertragen. Bitte Werte unter environment eintragen; Beispieldateien nicht als echte Zugangsdaten verwenden.')
        for mount in (service.get('volumes') or []):
            if isinstance(mount, str):
                chunks = mount.split(':')
                if len(chunks) < 2:
                    continue
                source, target = chunks[:2]
            elif isinstance(mount, dict) and mount.get('type') == 'bind':
                source, target = mount.get('source', ''), mount.get('target', '')
            else:
                continue
            if (isinstance(source, str) and source.startswith(('./', '../'))
                    and _im_file_mount_expected(source, target)):
                messages.append(f'{service_name}: Datei-Mount {source} → {target} benötigt eine echte Datei auf dem NAS. Install Monitor importiert keine Dateien neben der Compose; bitte zuerst die Herstellerdatei bereitstellen und den Mount auf deren absoluten NAS-Pfad ändern.')
    return messages[:50]


def _warnings(data: dict) -> list[str]:
    notes = []
    for name, svc in data["services"].items():
        for risk in PRIVILEGED_KEYS:
            if risk in svc and svc[risk] not in (False, None):
                notes.append(f"{name}: erweiterter Docker-Zugriff ({risk})")
        if svc.get("env_file"):
            notes.append(f"{name}: env_file benötigt zusätzliche Dateien und wird nicht automatisch importiert")
        for port in svc.get("ports", []) or []:
            if isinstance(port, str):
                found = re.match(r"^(\d+):(\d+)", port)
                if found and int(found.group(1)) in RESERVED:
                    notes.append(f"{name}: Host-Port {found.group(1)} ist reserviert oder wird für Install Monitor benötigt")
    if _unresolved_runtime_variables(data):
        notes.append("Unaufgelöste ${VARIABLEN}: vor der Installation konkrete Werte eintragen")
    notes.extend(_im_compose_external_file_issues(data))
    notes.extend(_compose_mount_name_issues(data))
    return notes


def _compose_mount_name_issues(data: dict) -> list[str]:
    """Flag undeclared named volumes without guessing a new storage location.

    The Compose spec expects service-used named volumes to be declared at the
    top level. Docker may accept some loose forms; do not silently invent an
    external volume or create an incorrect bind mount on ZimaOS.
    """
    volumes = data.get('volumes') or {}
    if not isinstance(volumes, dict):
        return ['Compose: Top-Level-volumes muss eine Zuordnung sein.']
    missing = set()
    for service_name, service in data['services'].items():
        for mount in service.get('volumes') or []:
            if isinstance(mount, str):
                parts = mount.split(':')
                if len(parts) < 2:
                    continue  # Anonymous mount, e.g. /config, belongs to its service.
                candidate = parts[0].strip()
            elif isinstance(mount, dict) and mount.get('type') == 'volume':
                candidate = str(mount.get('source') or '').strip()
            else:
                continue
            if not candidate or candidate.startswith(('/', './', '../', '~', '$')):
                continue
            if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', candidate) and candidate not in volumes:
                missing.add((service_name, candidate))
    return [f'{service}: Docker-Volume {volume} ist im Top-Level-volumes-Block nicht definiert.'
            for service, volume in sorted(missing)]


def _im_safe_relative_bind(source: str, root: str) -> str | None:
    """Canonical mapping for a relative bind, independent of service name.

    The source path belongs to the *Compose project*, not one service. Reject
    traversal and special paths instead of flattening them to a possibly wrong
    directory or surprising host location.
    """
    if not isinstance(source, str) or not source.startswith('./'):
        return None
    fragments = source.split('/')[1:]
    if not fragments or any(p in ('', '..') or '\\' in p or ':' in p or '\x00' in p for p in fragments):
        return None
    resolved = root.rstrip('/') + '/' + '/'.join(p for p in fragments if p != '.')
    if resolved == root.rstrip('/') or len(resolved) > 500:
        return None
    return resolved


# v0.2.45: Synology DSM bind-source adaptation; never change named volumes.
_SYNOLOGY_DOCKER_SOURCE = re.compile(r'^/volume[0-9]+/docker/([A-Za-z0-9_.-]+)(/.*)?$')


def _im_convert_synology_binds(doc: dict, app_name: str, base: str) -> list[str]:
    """Map /volumeN/docker/<project>/... to a ZimaOS app-owned root.

    This does not touch the upstream container target, permissions mode,
    named volumes, credentials or an existing /DATA path. Unrecognized DSM
    storage paths are reported rather than guessed or created in the host OS.
    """
    notes: list[str] = []
    changed = []
    for svc_name, service in doc['services'].items():
        mounts = service.get('volumes') or []
        if not isinstance(mounts, list):
            continue
        for index, mount in enumerate(mounts):
            long_form = isinstance(mount, dict) and mount.get('type') == 'bind'
            if isinstance(mount, str):
                parts = mount.split(':', 2)
                if len(parts) < 2 or not parts[0].startswith('/'):
                    continue
                source = parts[0]
            elif long_form:
                source = mount.get('source')
            else:
                continue
            if not isinstance(source, str):
                continue
            match = _SYNOLOGY_DOCKER_SOURCE.fullmatch(source)
            if not match:
                if re.match(r'^/volume[0-9]+(?:/|$)', source):
                    notes.append(f'{svc_name}: Synology-Pfad {source} nicht automatisch übertragen; NAS-Ziel manuell wählen.')
                continue
            project, suffix = match.groups()
            # project folders are not trusted for traversal, even if the regex
            # would allow dotted names.
            if project in ('.', '..') or any(part in ('', '.', '..') for part in (suffix or '').split('/')[1:]):
                notes.append(f'{svc_name}: Ungültiger Synology-Pfad {source}; bitte manuell korrigieren.')
                continue
            # /volume1/docker/wordpress maps to /DATA/AppData/wordpress,
            # not /DATA/AppData/wordpress/wordpress. Distinct project
            # folders stay separately namespaced under the selected app root.
            segment = '' if project.casefold() == app_name.casefold() else '/' + project
            mapped = base.rstrip('/') + segment + (suffix or '')
            # A WordPress document root MUST NOT contain sibling MariaDB or
            # Redis storage. The original DSM recipe nests db/redis beneath
            # the publicly served /var/www/html host bind, potentially
            # exposing database files over HTTP. Isolate web content.
            target = (parts[1] if isinstance(mount, str) else mount.get('target'))
            if (str(service.get('image','')).lower().startswith('wordpress:')
                    and target == '/var/www/html' and not suffix):
                mapped = base.rstrip('/') + '/html'
                notes.append(f'{svc_name}: öffentliches WordPress-Webverzeichnis nach {mapped} isoliert; db/redis bleiben außerhalb des Webroots.')
            if len(mapped) > 500:
                notes.append(f'{svc_name}: Synology-Mount-Pfad zu lang, bitte manuell bearbeiten.')
                continue
            if isinstance(mount, str):
                parts[0] = mapped
                mounts[index] = ':'.join(parts)
            else:
                mount['source'] = mapped
            changed.append(f'{svc_name}: {source} → {mapped}')
    if changed:
        notes.append('Synology-Docker-Pfade nach ZimaOS übertragen (Containerziele und ro/rw unverändert): ' + '; '.join(changed[:12]))
    return notes


def _im_unconverted_synology_binds(doc: dict) -> list[str]:
    issues = []
    for svcname, service in doc.get('services', {}).items():
        if not isinstance(service, dict) or service.get('profiles'):
            continue
        for mount in service.get('volumes') or []:
            source = (mount.split(':', 1)[0] if isinstance(mount, str)
                      else mount.get('source') if isinstance(mount, dict) and mount.get('type') == 'bind'
                      else '')
            if isinstance(source, str) and re.match(r'^/volume[0-9]+(?:/|$)', source):
                issues.append(f'{svcname}: Synology-Pfad {source} ist auf ZimaOS nicht nutzbar. Bitte einen Host-Pfad unter /DATA oder /media wählen.')
    return issues[:30]


def _im_wordpress_network_references(doc: dict) -> list[str]:
    """For DSM imports, normalize hostnames used as DB service aliases.

    Compose DNS guarantees the service name. A container's hostname is not
    a portable substitute for a Compose service network alias.
    """
    notes = []
    aliases = {str(svc.get('hostname')): name for name, svc in doc['services'].items()
               if isinstance(svc, dict) and isinstance(svc.get('hostname'), str)}
    for name, svc in doc['services'].items():
        if not isinstance(svc, dict):
            continue
        image = str(svc.get('image', '')).lower()
        if not (image.startswith('phpmyadmin:') or image == 'phpmyadmin'):
            continue
        host = _get_service_environment(svc, 'PMA_HOST')
        if host in aliases and aliases[host] != host:
            _set_service_environment(svc, 'PMA_HOST', aliases[host])
            notes.append(f'{name}: PMA_HOST auf Compose-Dienstname {aliases[host]} gesetzt (statt Container-Hostname {host}).')
    return notes


def _im_wordpress_dependency_cleanup(doc: dict) -> list[str]:
    """A WordPress site does not need a DB-admin UI to start.

    Remove only phpMyAdmin dependencies that can deadlock the frontend if
    its optional check fails. Keep other author-specified dependencies.
    """
    notes = []
    admin = {name for name, svc in doc['services'].items()
             if str(svc.get('image', '')).lower().startswith('phpmyadmin')}
    for name, svc in doc['services'].items():
        if not str(svc.get('image', '')).lower().startswith('wordpress:'):
            continue
        depends = svc.get('depends_on')
        if isinstance(depends, dict):
            for service in admin.intersection(depends):
                depends.pop(service)
                notes.append(f'{name}: Startabhängigkeit von {service} entfernt; phpMyAdmin ist nur ein Verwaltungswerkzeug. DB-/Redis-Abhängigkeiten bleiben unverändert.')
        elif isinstance(depends, list):
            removed = admin.intersection(depends)
            if removed:
                svc['depends_on'] = [dep for dep in depends if dep not in removed]
                notes.append(f'{name}: Startabhängigkeit von {", ".join(sorted(removed))} entfernt; phpMyAdmin ist optional.')
    return notes


def _im_wordpress_credentials_issues(doc: dict) -> list[str]:
    issues = []
    for name, svc in doc['services'].items():
        if not str(svc.get('image', '')).lower().startswith('wordpress:'):
            continue
        db_host = _get_service_environment(svc, 'WORDPRESS_DB_HOST')
        db_service = db_host.split(':', 1)[0]
        if db_service not in doc['services']:
            continue
        db = doc['services'][db_service]
        if not str(db.get('image','')).lower().startswith(('mariadb:', 'mysql:')):
            continue
        checks = [('WORDPRESS_DB_USER', 'MYSQL_USER'), ('WORDPRESS_DB_PASSWORD', 'MYSQL_PASSWORD'),
                  ('WORDPRESS_DB_NAME', 'MYSQL_DATABASE')]
        for wk, mk in checks:
            a, b = _get_service_environment(svc, wk), _get_service_environment(db, mk)
            if a and b and a != b:
                issues.append(f'{name}/{db_service}: {wk} und {mk} müssen übereinstimmen.')
    return issues


def _im_wordpress_shared_recipient_keys(doc: dict, service: str, key: str) -> list[tuple[str, str]]:
    """Sync WordPress DB credentials to its MariaDB service by exact DB_HOST."""
    suffixes = {'WORDPRESS_DB_USER': 'MYSQL_USER', 'WORDPRESS_DB_PASSWORD': 'MYSQL_PASSWORD',
                'WORDPRESS_DB_NAME': 'MYSQL_DATABASE'}
    mirrors = {v: k for k, v in suffixes.items()}
    result = [(service, key)]
    for wp, wp_svc in doc['services'].items():
        if not str(wp_svc.get('image','')).lower().startswith('wordpress:'):
            continue
        db = _get_service_environment(wp_svc, 'WORDPRESS_DB_HOST').split(':', 1)[0]
        if db not in doc['services'] or not str(doc['services'][db].get('image','')).lower().startswith(('mariadb:', 'mysql:')):
            continue
        if (service, key) == (wp, key) and key in suffixes:
            result.append((db, suffixes[key]))
        if (service, key) == (db, key) and key in mirrors:
            result.append((wp, mirrors[key]))
    return list(dict.fromkeys(result))


def _im_wordpress_weak_password_issues(doc: dict) -> list[str]:
    """Require changing publisher example credentials in imported WP stacks."""
    issues = []
    for name, svc in doc.get('services', {}).items():
        if not isinstance(svc, dict) or svc.get('profiles'):
            continue
        image = str(svc.get('image','')).lower()
        if not image.startswith(('wordpress:', 'mariadb:', 'mysql:')):
            continue
        # Narrow rule: WordPress + MariaDB example stacks, not unrelated apps.
        if not any(str(other.get('image','')).lower().startswith('wordpress:')
                   for other in doc['services'].values() if isinstance(other,dict)):
            continue
        for key, value in _im_environment_entries(svc).items():
            if not key.upper().endswith(('_PASSWORD', '_PASSWD')):
                continue
            value = str(value or '')
            if value and (len(value) < 12 or value.casefold().startswith(('change_me', 'replace_me', 'hier_sicheres_', 'your_password')) or value.casefold() in
                          {'password','rootpass','admin123','mariuspassword','changeme','change_me','example','123456789012'}):
                issues.append(f'{name}: {key} verwendet ein kurzes oder bekanntes Beispielpasswort. Bitte unter Zugangsdaten mit „Neu erzeugen“ ersetzen.')
    return issues


def _im_wordpress_ini_templates(doc: dict, app_name: str) -> dict[str, str]:
    """Known safe static template. Never fabricate other vendor config files."""
    approved = {}
    prefix = f'/DATA/AppData/{app_name}/'
    for svc in doc['services'].values():
        if not str(svc.get('image', '')).lower().startswith('wordpress:'):
            continue
        for mount in svc.get('volumes') or []:
            if isinstance(mount, str):
                parts = mount.split(':', 2)
                if len(parts) < 2: continue
                source, target = parts[:2]
            elif isinstance(mount, dict) and mount.get('type') == 'bind':
                source, target = mount.get('source'), mount.get('target')
            else:
                continue
            if (isinstance(source, str) and source.startswith(prefix)
                    and source.endswith('/uploads.ini')
                    and target == '/usr/local/etc/php/conf.d/uploads.ini'
                    and not any(part in ('', '.', '..') for part in source[len(prefix):].split('/'))):
                approved[source] = 'file_uploads=On\nmemory_limit=256M\nupload_max_filesize=64M\npost_max_size=64M\nmax_execution_time=300\n'
    return approved


def _convert_volumes(data: dict, name: str, base: str) -> None:
    """Make ZimaOS Compose preserve upstream Docker storage semantics.

    Named Docker volumes are *not* NAS bind folders. Rewriting them to a path
    removes Docker's image-content/ownership initialization and, previously,
    broke sharing by inserting a per-service prefix. Keep the author's volume
    declarations intact so users who prefer AppData can explicitly select
    bind mounts with their own ownership and backup policy.

    A relative host bind is relative to the project, not the service. Convert
    `./foo` to base/foo identically for every service, while preserving ro/rw
    flags. File mounts and parent traversals remain unchanged and are blocked
    by preflight until the user supplies a real absolute NAS path.
    """
    original = data.get('volumes')
    if original is not None and not isinstance(original, dict):
        raise HTTPException(400, 'Ungültiger Compose-volumes-Block.')
    for service_name, service in data['services'].items():
        changed = []
        for mount in service.get('volumes') or []:
            if isinstance(mount, str):
                parts = mount.split(':')
                if len(parts) >= 2 and parts[0].startswith(('./', '../')):
                    if _im_file_mount_expected(parts[0], parts[1]):
                        changed.append(mount)
                        continue
                    mapped = _im_safe_relative_bind(parts[0], base)
                    if mapped:
                        parts[0] = mapped
                        mount = ':'.join(parts)
                # Named and anonymous Docker volumes are unmodified.
            elif isinstance(mount, dict) and mount.get('type') == 'bind':
                old_source = mount.get('source')
                target = mount.get('target')
                if isinstance(old_source, str) and old_source.startswith(('./', '../')):
                    if _im_file_mount_expected(old_source, target):
                        changed.append(mount)
                        continue
                    mapped = _im_safe_relative_bind(old_source, base)
                    if mapped:
                        mount['source'] = mapped
                # The long-form mount's read_only, bind options, propagation,
                # etc. remain as declared by the publisher.
            changed.append(mount)
        if changed:
            service['volumes'] = changed
    # In particular do NOT drop data['volumes'] – this also preserves external,
    # local-driver options, project-scoped names, labels, and driver settings.


# Standard Docker service label, retained by ZimaOS. The deferred flag is
# only valid on its matching Cloudflare/Tailscale service, never on the app.
SETUP_LATER_LABEL = "io.github.isanto1306.install-monitor.setup-later"
SUPPORTED_SETUP_LATER = {"tailscale", "tunnel"}


def _service_setup_later(service: dict) -> str:
    labels = service.get("labels") or {}
    if isinstance(labels, dict):
        value = labels.get(SETUP_LATER_LABEL, "")
    elif isinstance(labels, list):
        candidates = [x.split("=", 1)[1] for x in labels if isinstance(x, str) and x.startswith(SETUP_LATER_LABEL + "=")]
        value = candidates[-1] if candidates else ""
    else:
        value = ""
    profile = str(value)
    image = str(service.get("image", "")).lower()
    if profile == "tailscale" and "tailscale/tailscale" in image:
        return profile
    if profile == "tunnel" and "cloudflare/cloudflared" in image:
        return profile
    return ""


def _set_setup_later(service: dict, profile: str) -> None:
    labels = service.setdefault("labels", {})
    if isinstance(labels, dict):
        labels[SETUP_LATER_LABEL] = profile
    elif isinstance(labels, list):
        labels[:] = [x for x in labels if not (isinstance(x, str) and x.startswith(SETUP_LATER_LABEL + "="))]
        labels.append(SETUP_LATER_LABEL + "=" + profile)
    else:
        raise HTTPException(400, "Ungültige Docker-Labels im Original-Compose.")


def _setup_later_options(doc: dict, selected: list[str]) -> list[dict]:
    # Show this choice only for profiles actually selected and matching a known
    # service. An unknown optional service must not bypass prerequisite checks.
    options = []
    for service_name, svc in doc["services"].items():
        for profile in (svc.get("profiles") or []):
            if profile not in selected or profile not in SUPPORTED_SETUP_LATER:
                continue
            image = str(svc.get("image", "")).lower()
            if (profile == "tunnel" and "cloudflare/cloudflared" in image) or (profile == "tailscale" and "tailscale/tailscale" in image):
                options.append({"profile": profile, "service": service_name})
    return options


def _setup_issues(data: dict) -> list[str]:
    """Preflight active selected services, without altering source definitions."""
    errors = _im_compose_external_file_issues(data) + _compose_mount_name_issues(data) + _im_sample_mount_issues(data)
    for service_name, service in data['services'].items():
        for mount in service.get('volumes') or []:
            if isinstance(mount, str):
                pieces = mount.split(':')
                if len(pieces) < 2:
                    continue
                source = pieces[0]
            elif isinstance(mount, dict) and mount.get('type') == 'bind':
                source = str(mount.get('source') or '')
            else:
                continue
            if source.startswith(('./', '../')):
                errors.append(f'{service_name}: Relativer Bind-Mount {source} benötigt eine absolute NAS-Quelle oder eine eindeutige Projektpfadzuordnung.')
    for name, service in data['services'].items():
        image = str(service.get('image', '')).lower()
        if 'tailscale/tailscale' in image:
            if _service_setup_later(service) == 'tailscale':
                continue
            if not (_get_service_environment(service, 'TS_AUTHKEY') or _get_service_environment(service, 'TS_OAUTH_CLIENT_SECRET')):
                errors.append(f'{name}: Tailscale-Schlüssel fehlt. Für spätere Einrichtung Profil deaktivieren; für sofortige Installation Schlüssel eingeben.')
        if 'cloudflare/cloudflared' in image:
            if _service_setup_later(service) == 'tunnel':
                continue
            cmd = service.get('command', '')
            command = ' '.join(map(str,cmd)) if isinstance(cmd,list) else str(cmd)
            if 'tunnel' in command and 'run' in command:
                has_token = any(_get_service_environment(service,key) for key in ('TUNNEL_TOKEN', 'CLOUDFLARE_TUNNEL_TOKEN'))
                has_config = any('/etc/cloudflared' in str(vol) for vol in (service.get('volumes') or []))
                if not has_token and not has_config:
                    errors.append(f'{name}: Cloudflare Tunnel benötigt Token oder eingebundene Tunnel-Konfiguration. Nur TUNNEL_URL genügt für „tunnel run“ nicht.')
    return errors


# v0.2.23: ZimaOS-specific checks on the *final* YAML.  Adapted from
# documented zimapp design ideas, independently implemented; do not assume
# undocumented beta firmware behavior is universal.  Never edit source values.
def _im_published_host_ports(service: dict) -> set[str]:
    """Host ports of the WebUI service; preserve the distinction from targets."""
    ports: set[str] = set()
    for entry in service.get('ports') or []:
        if isinstance(entry, dict):
            published = entry.get('published')
            if published is not None and str(published).isdigit():
                ports.add(str(int(str(published))))
        elif isinstance(entry, str):
            spec = entry.rsplit('/', 1)[0] if entry.rsplit('/', 1)[-1] in ('tcp', 'udp', 'sctp') else entry
            fields = spec.rsplit(':', 2)
            if len(fields) >= 2 and fields[-2].isdigit():
                ports.add(str(int(fields[-2])))
    return ports


def _im_zimaos_contract_checks(doc: dict) -> tuple[list[str], list[str]]:
    """Local preflight.  Errors block installation, advisory checks stay visible.

    Do not require ports for headless apps or guess a WebUI for one that has none.
    All declared docker named-volumes are left unchanged by this validator.
    """
    errors: list[str] = []
    warnings: list[str] = []
    services = doc.get('services', {})
    if not isinstance(services, dict) or not services:
        return ['ZimaOS: Compose hat keine Dienste.'], []
    casa = doc.get('x-casaos')
    if not isinstance(casa, dict):
        return ['ZimaOS: x-casaos fehlt.'], []
    main = casa.get('main')
    if not isinstance(main, str) or main not in services:
        errors.append('ZimaOS: x-casaos.main muss einen vorhandenen Hauptdienst bezeichnen.')
    port_map = casa.get('port_map')
    if port_map is not None and not isinstance(port_map, str):
        errors.append('ZimaOS: x-casaos.port_map muss eine Zeichenfolge sein (z. B. "8080").')
    if isinstance(main, str) and main in services:
        service = services[main]
        if isinstance(service, dict):
            published = _im_published_host_ports(service)
            if isinstance(port_map, str) and port_map.strip() and published and port_map.strip() not in published:
                errors.append('ZimaOS: x-casaos.port_map ' + port_map[:20]
                              + ' passt nicht zu den Host-Ports des Hauptdienstes '
                              + main + ' (' + ', '.join(sorted(published))[:100] + ').')
            elif not str(port_map or '').strip():
                warnings.append('ZimaOS: Kein WebUI-Port für die Dashboard-Kachel ermittelt; bei Headless-Apps zulässig.')
    for name, service in services.items():
        if not isinstance(service, dict):
            errors.append(f'{name}: Dienstkonfiguration ist kein YAML-Objekt.')
            continue
        dependencies = service.get('depends_on') or []
        if not isinstance(dependencies, (dict, list)):
            errors.append(f'{name}: depends_on benötigt eine Liste oder Zuordnung.')
        else:
            for dependency in (dependencies if isinstance(dependencies, dict) else dependencies):
                if dependency not in services:
                    errors.append(f'{name}: Abhängigkeit {str(dependency)[:70]} fehlt im Compose-Stack.')
        limits = ((service.get('deploy') or {}).get('resources') or {}).get('limits') or {}
        for field in ('memory', 'cpus'):
            value = limits.get(field) if isinstance(limits, dict) else None
            if value is not None and ',' in str(value):
                errors.append(f'{name}: Ressourcenlimit {field} muss einen Punkt statt Komma verwenden.')
        for entry in service.get('ports') or []:
            if isinstance(entry, dict) and entry.get('published') is not None and not isinstance(entry['published'], str):
                errors.append(f'{name}: Veröffentlichter Port muss als Zeichenfolge angegeben werden.')
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))


def _project_image_issues(data: dict, name: str) -> list[str]:
    """Detect clearly project-specific bare/local image tags before install."""
    author = str((data.get('x-casaos') or {}).get('author') or '') if isinstance(data.get('x-casaos'), dict) else ''
    if not author:
        return []
    errors=[]
    for service_name, service in data['services'].items():
        image = str(service.get('image', ''))
        repository = image.split(':', 1)[0]
        if repository == name and '/' not in repository and not local_image_available(image):
            errors.append(f"{service_name}: Projekt-Image '{image}' ist lokal nicht vorhanden. Das Originalprojekt muss dieses Image zuerst bauen, oder du wählst bewusst ein veröffentlichtes Image des Herstellers.")
    return errors


def optional_profiles(doc: dict) -> list[dict]:
    """Describe optional services without assuming they can all run on ZimaOS."""
    by_name: dict[str, dict] = {}
    for service_name, svc in doc['services'].items():
        for profile in svc.get('profiles', []) or []:
            if not isinstance(profile, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,50}', profile):
                raise HTTPException(400, f'{service_name}: Ungültiger Profilname.')
            item = by_name.setdefault(profile, {'name': profile, 'services': [], 'local_build': False})
            item['services'].append(service_name)
            if 'build' in svc and '/' not in str(svc.get('image', '')):
                item['local_build'] = True
    return list(by_name.values())


def select_profiles(doc: dict, selected_profiles: list[str], notes: list[str] | None = None, deferred_profiles: set[str] | None = None) -> dict:
    profiles = {x['name'] for x in optional_profiles(doc)}
    selected = set(selected_profiles)
    if len(selected) != len(selected_profiles) or not selected.issubset(profiles):
        raise HTTPException(400, 'Unbekannte oder doppelte optionale Compose-Profile.')
    inactive = set()
    for name, svc in list(doc['services'].items()):
        svc_profiles = svc.get('profiles', []) or []
        if svc_profiles and not selected.intersection(svc_profiles):
            inactive.add(name)
            del doc['services'][name]
            if notes is not None:
                if deferred_profiles and any(p in deferred_profiles for p in svc_profiles):
                    notes.append(f'{name}: Optionaler Dienst für diese Installation zurückgestellt.')
                else:
                    notes.append(f'{name}: Optionaler Dienst nicht ausgewählt.')
        elif svc_profiles:
            svc.pop('profiles', None)
            if notes is not None:
                notes.append(f'{name}: Optionaler Dienst ausdrücklich ausgewählt.')
    if not doc['services']:
        raise HTTPException(400, 'Die Auswahl enthält keine installierbaren Dienste.')
    for name, svc in doc['services'].items():
        depends = svc.get('depends_on', []) or []
        names = depends.keys() if isinstance(depends, dict) else depends
        for dependency in names:
            if dependency in inactive:
                raise HTTPException(400, f'{name}: benötigt den nicht ausgewählten optionalen Dienst {dependency}.')
    return doc


def _normalize_legacy_env_files(doc: dict, notes: list[str]) -> None:
    """Protect ZimaOS's older compose-go parser from object-form env_file.

    The ZimaOS compose-install API receives only YAML, not repository-side
    .env files. Optional env_file objects (required: false) cannot supply
    runtime values on that endpoint; remove them after warning the user.
    Required env files instead need explicit environment entries: never
    invent their contents or turn an optional source into a required one.
    """
    for service_name, svc in doc['services'].items():
        env_files = svc.get('env_file')
        if env_files is None:
            continue
        if isinstance(env_files, (str, dict)):
            entries = [env_files]
        elif isinstance(env_files, list):
            entries = env_files
        else:
            raise HTTPException(400, f"{service_name}: Ungültige env_file-Konfiguration.")
        kept = []
        for entry in entries:
            if isinstance(entry, str):
                kept.append(entry)
                continue
            if not isinstance(entry, dict) or not isinstance(entry.get('path'), str) or not entry['path'].strip():
                raise HTTPException(400, f"{service_name}: Ungültiger env_file-Eintrag.")
            path = entry['path'].strip()
            if entry.get('required', True) is not False:
                raise HTTPException(400, f"{service_name}: Pflicht-env_file '{path}' kann nicht aus dem GitHub-Repository an ZimaOS übertragen werden. Werte bitte als environment: im Compose eintragen.")
            notes.append(f"{service_name}: Optionale env_file '{path}' entfernt: ZimaOS akzeptiert die neue Objekt-Schreibweise nicht; ihre Datei wird über den Installationsauftrag ohnehin nicht übertragen. Benötigte Werte direkt unter environment: eintragen.")
        if kept:
            svc['env_file'] = kept
        else:
            svc.pop('env_file', None)


def _validate_legacy_env_files(doc: dict) -> None:
    """Reject object-form env_file in an edited Compose before the ZimaOS POST."""
    for service_name, svc in doc['services'].items():
        entries = svc.get('env_file')
        if entries is None:
            continue
        if isinstance(entries, str):
            continue
        if not isinstance(entries, list) or any(not isinstance(e, str) for e in entries):
            raise HTTPException(400, f"{service_name}: ZimaOS unterstützt bei env_file nur Zeichenketten, keine path/required-Objekte. Bitte den Entwurf neu erstellen.")


def _set_service_environment(svc: dict, key: str, value: str) -> None:
    env = svc.setdefault('environment', [])
    if isinstance(env, list):
        for i, item in enumerate(env):
            if isinstance(item, str) and item.split('=',1)[0] == key:
                env[i] = key + '=' + value
                return
        env.append(key + '=' + value)
    elif isinstance(env, dict):
        env[key] = value
    else:
        raise HTTPException(400, 'Unbekanntes Format der Umgebungsvariablen.')


def _get_service_environment(svc: dict, key: str) -> str:
    env = svc.get('environment', []) or []
    if isinstance(env, dict):
        return str(env.get(key) or '')
    if isinstance(env, list):
        for item in env:
            if isinstance(item, str) and item.startswith(key + '='):
                return item.split('=', 1)[1]
    return ''


def inspect_local_image_metadata(image: str) -> dict | None:
    """Read-only inspection; never pull, create or run a Docker container."""
    if not IMAGE.fullmatch(image) or image.startswith('-'):
        return None
    try:
        proc = subprocess.run(['docker', 'image', 'inspect', '--', image],
                              capture_output=True, text=True, timeout=8, check=False)
        # Some Docker versions do not accept -- in this command.
        if proc.returncode != 0:
            proc = subprocess.run(['docker', 'image', 'inspect', image],
                                  capture_output=True, text=True, timeout=8, check=False)
        if proc.returncode != 0 or len(proc.stdout) > 1_500_000:
            return None
        results = json.loads(proc.stdout)
        if not isinstance(results, list) or not results or not isinstance(results[0], dict):
            return None
        item = results[0]
        cfg = item.get('Config') or {}
        if not isinstance(cfg, dict):
            return None
        return {'config': cfg, 'architecture': item.get('Architecture'),
                'os': item.get('Os'), 'size': item.get('Size')}
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        return None



# v0.2.0 preview: deterministic, read-only remote OCI metadata analysis.
# Trusted registries only, to avoid SSRF via user-supplied image references.
def inspect_remote_image_metadata(image: str) -> tuple[dict | None, str]:
    """Read anonymous Docker Hub / GHCR image config, never pull/start images.

    This is not a source of mandatory setup variables or multi-service dependencies.
    """
    if not IMAGE.fullmatch(image) or '@' in image or image.startswith('-'):
        return None, 'Remote OCI-Analyse unterstützt nur einfache Image-Tags.'
    target = image.strip()
    first = target.split('/')[0].lower()
    if first in ('docker.io', 'index.docker.io', 'registry-1.docker.io'):
        target = '/'.join(target.split('/')[1:])
        registry = 'registry-1.docker.io'
    elif first == 'ghcr.io':
        target = '/'.join(target.split('/')[1:]); registry = 'ghcr.io'
    elif '/' not in target or ('.' not in first and ':' not in first):
        registry = 'registry-1.docker.io'
    else:
        return None, 'Registry nicht unterstützt: Es werden nur Docker Hub und GHCR anonym gelesen.'
    if not target or target.startswith('/') or '..' in target.split('/'):
        return None, 'Ungültiger Repository-Pfad.'
    if registry == 'registry-1.docker.io' and '/' not in target:
        target = 'library/' + target
    if ':' in target.rsplit('/', 1)[-1]:
        repo, tag = target.rsplit(':', 1)
    else:
        repo, tag = target, 'latest'
    if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', repo) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', tag):
        return None, 'Registry-Pfad oder Tag nicht unterstützt.'
    base_url = 'https://' + registry + '/v2/' + repo
    accept = ', '.join((
        'application/vnd.oci.image.index.v1+json',
        'application/vnd.docker.distribution.manifest.list.v2+json',
        'application/vnd.oci.image.manifest.v1+json',
        'application/vnd.docker.distribution.manifest.v2+json'))
    token = ''
    if registry == 'registry-1.docker.io':
        auth_url = 'https://auth.docker.io/token?' + urllib.parse.urlencode({
            'service': 'registry.docker.io', 'scope': 'repository:' + repo + ':pull'})
        try:
            with urllib.request.urlopen(urllib.request.Request(auth_url,headers={'User-Agent':'InstallMonitor/0.2'}),timeout=6) as r:
                if int(r.headers.get('Content-Length','0') or 0) > 32768: return None,'Zu große Registry-Antwort.'
                token = json.loads(r.read(32769)).get('token','')
        except (OSError, ValueError, KeyError) as ex:
            return None, 'Docker-Hub-Authentifizierung fehlgeschlagen: '+type(ex).__name__
        if not token: return None,'Kein anonymes Registry-Token verfügbar.'

    def fetch(path: str, accept_type: str, limit: int = 524288) -> dict:
        nonlocal token
        req = urllib.request.Request(base_url + '/' + path, headers={
            'Accept': accept_type, 'User-Agent':'InstallMonitor/0.2',
            **({'Authorization':'Bearer '+token} if token else {})})
        # Enforce HTTPS and allowed host for initial URL. urllib may redirect;
        # redirect hosts must not be trusted except canonical OCI blob CDN.
        try:
            response = urllib.request.urlopen(req, timeout=8)
        except urllib.error.HTTPError as exc:
            if exc.code != 401 or token or registry != 'ghcr.io':
                raise
            challenge = exc.headers.get('WWW-Authenticate', '')
            # Never fetch a token from an arbitrary authentication realm.
            if not challenge.lower().startswith('bearer '):
                raise
            realm = re.search(r'realm="([^"]+)"', challenge)
            scope = re.search(r'scope="([^"]+)"', challenge)
            service = re.search(r'service="([^"]+)"', challenge)
            if (not realm or realm.group(1) != 'https://ghcr.io/token' or
                    (scope and scope.group(1) != 'repository:' + repo + ':pull') or
                    (service and service.group(1) != 'ghcr.io')):
                raise
            auth_url = 'https://ghcr.io/token?' + urllib.parse.urlencode({
                'service': 'ghcr.io', 'scope': 'repository:' + repo + ':pull'})
            with urllib.request.build_opener(NoRedirect()).open(
                urllib.request.Request(auth_url, headers={'User-Agent':'InstallMonitor/0.2'}),
                timeout=6) as auth_response:
                raw_token = auth_response.read(32769)
            if len(raw_token) > 32768: raise ValueError('GHCR token too large')
            token = str(json.loads(raw_token).get('token') or '')
            if not token: raise ValueError('No anonymous GHCR token')
            return fetch(path, accept_type, limit)
        with response:
            url = urllib.parse.urlsplit(response.geturl())
            if url.scheme != 'https' or url.hostname not in (
                'registry-1.docker.io', 'ghcr.io', 'production.cloudflare.docker.com',
                'docker-images-prod.6aa30f8b08e16409b46e0173d6de2f56.r2.cloudflarestorage.com'):
                raise ValueError('Unerwartete Weiterleitung der Registry')
            raw = response.read(limit+1)
            if len(raw)>limit: raise ValueError('Registry-Antwort zu groß')
        data=json.loads(raw)
        if not isinstance(data,dict): raise ValueError('Ungültige OCI-Struktur')
        return data
    try:
        manifest=fetch('manifests/'+urllib.parse.quote(tag,safe=''),accept)
        if 'manifests' in manifest:
            candidates=[m for m in manifest.get('manifests',[]) if isinstance(m,dict) and
                        (m.get('platform') or {}).get('os')=='linux' and
                        (m.get('platform') or {}).get('architecture')=='amd64']
            if not candidates:
                return None,'Keine Linux/amd64-Variante in den OCI-Manifests gefunden.'
            digest=str(candidates[0].get('digest',''))
            if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest): raise ValueError('Ungültiger Manifest-Digest')
            manifest=fetch('manifests/'+digest,accept)
        config=manifest.get('config') or {}
        digest=str(config.get('digest',''))
        if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest): raise ValueError('Kein gültiger Image-Konfigurationsdigest')
        size=int(config.get('size',0) or 0)
        if size>524288: return None,'Image-Konfiguration überschreitet Größenlimit.'
        cfg=fetch('blobs/'+digest,'application/vnd.oci.image.config.v1+json, application/vnd.docker.container.image.v1+json')
        if not isinstance(cfg.get('config'),dict): raise ValueError('Konfigurationsdaten fehlen')
        return {'config':cfg['config'],'os':cfg.get('os'),'architecture':cfg.get('architecture')},''
    except (OSError,ValueError,TypeError,KeyError,urllib.error.HTTPError) as exc:
        return None,'Remote OCI-Metadaten nicht verfügbar: '+type(exc).__name__

def _metadata_compose_draft(image: str, appname: str, metadata: dict) -> tuple[dict, list[str]]:
    """Conservative single-image draft using only declared, inspectable metadata."""
    cfg = metadata['config']
    service: dict[str, Any] = {'image': image, 'restart': 'unless-stopped'}
    notes = ['Docker-Image-Metadaten des lokal vorhandenen Images analysiert (ohne Containerstart).']
    platform = '/'.join(str(metadata.get(x) or '') for x in ('os', 'architecture')).strip('/')
    if platform:
        notes.append(f'Image-Plattform: {platform}. Architektur-Kompatibilität mit dem ZimaOS-Host prüfen.')
    ports = cfg.get('ExposedPorts') or {}
    port_candidates = []
    if isinstance(ports, dict):
        for key in ports:
            match = re.fullmatch(r'([0-9]{1,5})/(tcp|udp)', str(key))
            if match and 1 <= int(match.group(1)) <= 65535:
                port_candidates.append((int(match.group(1)), match.group(2)))
    if len(port_candidates) == 1:
        port, protocol = port_candidates[0]
        if port not in RESERVED:
            service['ports'] = [f'{port}:{port}/{protocol}']
            notes.append(f'Image deklariert {port}/{protocol}; Host-Port {port} nur vorgeschlagen, vor Installation auf Konflikte prüfen.')
        else:
            notes.append(f'Image deklariert {port}/{protocol}; Host-Port muss wegen reservierter NAS-Ports manuell gewählt werden.')
    elif port_candidates:
        notes.append('Mehrere Container-Ports deklariert: ' + ', '.join(f'{p}/{proto}' for p, proto in port_candidates[:12]) + '. Benötigte Ports manuell zuordnen.')
    else:
        notes.append('Das Image deklariert keinen Container-Port. Web-Port nicht automatisch bestimmbar.')
    volumes = cfg.get('Volumes') or {}
    if isinstance(volumes, dict):
        paths = [v for v in volumes if isinstance(v, str) and v.startswith('/') and '..' not in v.split('/') and ':' not in v and len(v) <= 180]
        if paths:
            service['volumes'] = [f'/DATA/AppData/{appname}/volume-{i + 1}:{v}' for i, v in enumerate(paths[:8])]
            notes.append(f'{min(len(paths), 8)} deklarierte Image-Volumes als ZimaOS-AppData-Vorschläge aufgenommen; weitere Datenpfade laut Herstellerdokumentation prüfen.')
    env = cfg.get('Env') or []
    if isinstance(env, list):
        keys = [e.split('=', 1)[0] for e in env if isinstance(e, str) and '=' in e and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', e.split('=', 1)[0])]
        if keys:
            notes.append('Image deklariert Umgebungsvariablen: ' + ', '.join(keys[:25]) + '. Standardwerte werden nicht als sichere Zugangsdaten übernommen.')
    notes.append('Metadaten ersetzen keine Hersteller-Compose: versteckte Datenpfade, weitere Dienste, Zugangsdaten und Startvoraussetzungen müssen vor der Installation geprüft werden.')
    return {'name': appname, 'services': {appname: service}}, notes


def local_image_available(image: str) -> bool:
    """An image installed on the same ZimaOS host can be used without build context."""
    try:
        result = subprocess.run(['docker','image','inspect',image],capture_output=True,timeout=6)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def defer_missing_local_builds(doc: dict, selected_profiles: list[str], notes: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Compatibility API: never silently defer explicitly selected profiles.

    An author-provided local build must be fulfilled by a local image or reported
    as a prerequisite. The original source is never secretly substituted.
    """
    available = {item['name']: item for item in optional_profiles(doc)}
    if len(set(selected_profiles)) != len(selected_profiles) or not set(selected_profiles).issubset(available):
        raise HTTPException(400, 'Unbekannte oder doppelte optionale Compose-Profile.')
    if notes is not None:
        for profile in selected_profiles:
            for service_name in available[profile]['services']:
                service = doc['services'][service_name]
                if service.get('build') and not local_image_available(str(service['image'])):
                    notes.append(f'{service_name}: Original-Image für lokalen Build noch nicht vorhanden. Vor der Installation bereitstellen; Zusatzdienst wird NICHT automatisch entfernt.')
    return list(selected_profiles), []



_BUILD_META = 'x-install-monitor-github'
_CODEBERG_BUILD_META = 'x-install-monitor-codeberg'
_CODEBERG_REPO = re.compile(r'^https://codeberg\.org/([A-Za-z0-9_.-]{1,100})/([A-Za-z0-9_.-]{1,100})$')
_BUILD_REPO = re.compile(r'^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9_.-]{1,100})$')
_BUILD_SHA = re.compile(r'^[0-9a-f]{40}$')
_BUILD_IMG = re.compile(r'^installmonitor-local/[a-z0-9-]+:[0-9a-f]{12}$')


def _relative_build_path(path: str, allow_dot: bool = True) -> str:
    if not isinstance(path, str) or len(path) > 250 or '\\' in path or path.startswith('/'):
        raise HTTPException(400, 'Docker-Build-Pfad muss relativ zum Quell-Repository sein.')
    components = path.split('/')
    if not path or '..' in components or any(x == '' for x in components) or any(ord(c) < 32 for c in path):
        raise HTTPException(400, 'Unsicherer oder leerer Docker-Build-Pfad.')
    if not allow_dot and path in ('.', './'):
        raise HTTPException(400, 'Ein Dockerfile muss eine Datei benennen.')
    return path


_BUILD_OPTIONS_SUPPORTED = frozenset({'context', 'dockerfile', 'target', 'args', 'cache_from'})
_BUILD_TARGET_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
_BUILD_ARG_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,127}$')


def _validated_build_args(value: Any, service: str) -> list[str]:
    """Represent published Docker build args without shell parsing or env reads.

    Every value comes from the reviewed Compose after its default-variable
    expansion, never the user's host environment. No local interpolation,
    commands, secrets lookup, or execution before the separate build consent.
    """
    if value is None:
        return []
    raw_items = list(value.items()) if isinstance(value, dict) else []
    if isinstance(value, list):
        raw_items = []
        for item in value:
            if not isinstance(item, str) or '=' not in item:
                raise HTTPException(400, f'{service}: Build-Argumente benötigen explizite Werte im Format NAME=WERT.')
            raw_items.append(item.split('=', 1))
    elif not isinstance(value, dict):
        raise HTTPException(400, f'{service}: Ungültiges Format für Docker-Build-Argumente.')
    if len(raw_items) > 40:
        raise HTTPException(400, f'{service}: Zu viele Docker-Build-Argumente.')
    result = []
    names = set()
    for key, val in raw_items:
        if not isinstance(key, str) or not _BUILD_ARG_RE.fullmatch(key) or key in names:
            raise HTTPException(400, f'{service}: Ungültiger oder doppelter Name eines Docker-Build-Arguments.')
        names.add(key)
        if isinstance(val, bool):
            val = str(val).lower()
        elif isinstance(val, (int, float)) and not isinstance(val, bool):
            val = str(val)
        if not isinstance(val, str) or len(val) > 2048 or any(ord(c) < 32 for c in val):
            raise HTTPException(400, f'{service}: Ungültiger Docker-Build-Argumentwert für {key}.')
        if '${' in val or '$(' in val or '`' in val:
            raise HTTPException(400, f'{service}: Docker-Build-Argument {key} enthält einen nicht aufgelösten Ausdruck.')
        result.append(f'{key}={val}')
    return result


def _validated_build_cache(value: Any, service: str) -> list[str]:
    """Docker --cache-from images only; buildx cache backends aren't supported."""
    if value is None:
        return []
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or len(values) > 8:
        raise HTTPException(400, f'{service}: Ungültige Cache-Image-Liste für Docker-Build.')
    for ref in values:
        if not isinstance(ref, str) or not IMAGE.fullmatch(ref) or len(ref) > 200:
            raise HTTPException(400, f'{service}: Ungültiges Docker-Cache-Image. Nur Image-Referenzen erlaubt.')
    return values


def _validated_builds(doc: dict) -> list[dict]:
    builds = [(n, svc) for n, svc in doc['services'].items() if 'build' in svc]
    if not builds:
        return []
    github = doc.get(_BUILD_META)
    codeberg = doc.get(_CODEBERG_BUILD_META)
    if github is not None and codeberg is not None:
        raise HTTPException(400, 'Widersprüchliche Build-Quellen. Bitte die Originalquelle erneut analysieren.')
    metadata = github if github is not None else codeberg
    if not isinstance(metadata, dict):
        name, service = builds[0]
        raise HTTPException(400, f"{name}: Für das lokale Image '{service.get('image', '')}' fehlt ein verifizierter GitHub- oder Codeberg-Build-Kontext. Bitte die Originalquelle erneut analysieren.")
    repo = metadata.get('repository')
    sha = metadata.get('revision')
    compose_dir = metadata.get('compose_dir', '.')
    provider = 'codeberg' if codeberg is not None else 'github'
    valid_repo = (_CODEBERG_REPO.fullmatch(repo) if provider == 'codeberg'
                  else _BUILD_REPO.fullmatch(repo)) if isinstance(repo, str) else None
    if not valid_repo or not isinstance(sha, str) or not _BUILD_SHA.fullmatch(sha):
        raise HTTPException(400, 'Ungültiger oder unvollständiger Build-Quellennachweis.')
    branch = metadata.get('branch', '')
    if provider == 'codeberg' and (not isinstance(branch, str)
            or not re.fullmatch(r'[A-Za-z0-9._-]{1,120}', branch)
            or branch in ('.', '..')):
        raise HTTPException(400, 'Codeberg-Branch für gepinnten Build ungültig.')
    _relative_build_path(compose_dir)
    result = []
    for name, svc in builds:
        build = svc['build']
        build = {'context': build} if isinstance(build, str) else build
        if not isinstance(build, dict) or not isinstance(build.get('context', '.'), str):
            raise HTTPException(400, f'{name}: Ungültige Docker-Build-Konfiguration.')
        unsupported = set(build) - _BUILD_OPTIONS_SUPPORTED
        if unsupported:
            raise HTTPException(400, f'{name}: Docker-Build-Option(en) nicht unterstützt: {", ".join(sorted(map(str, unsupported)))}. Bitte ein fertiges Herausgeber-Image wählen.')
        context = _relative_build_path(build.get('context', '.'))
        dockerfile = _relative_build_path(build.get('dockerfile', 'Dockerfile'), False)
        target = build.get('target')
        if target is not None and (not isinstance(target, str) or not _BUILD_TARGET_RE.fullmatch(target)):
            raise HTTPException(400, f'{name}: Ungültiges Docker-Build-Target.')
        build_args = _validated_build_args(build.get('args'), name)
        cache_from = _validated_build_cache(build.get('cache_from'), name)
        repo_context = posixpath.normpath(posixpath.join(compose_dir, context))
        if repo_context == '..' or repo_context.startswith('../'):
            raise HTTPException(400, f'{name}: Docker-Kontext darf das Quell-Repository nicht verlassen.')
        image = svc.get('image')
        if not isinstance(image, str) or not _BUILD_IMG.fullmatch(image):
            raise HTTPException(400, f'{name}: Lokaler Build benötigt das vom Install Monitor erstellte Image-Tag.')
        if not image.endswith(':' + sha[:12]):
            raise HTTPException(400, f'{name}: Image-Tag und GitHub-Revision stimmen nicht überein.')
        result.append({'service': name, 'image': image, 'repo': repo, 'revision': sha,
                       'provider': provider, 'branch': branch,
                       'context': repo_context, 'dockerfile': dockerfile,
                       'target': target, 'args': build_args, 'cache_from': cache_from})
    return result


def _attach_github_build_context(doc: dict, project_url: str, resolved_url: str) -> tuple[dict, list[str]]:
    # Do not fabricate GitHub build context for pasted YAML or unsupported sources.
    match = _BUILD_REPO.fullmatch(project_url)
    raw = urllib.parse.urlsplit(resolved_url)
    pieces = [urllib.parse.unquote(x) for x in raw.path.strip('/').split('/')]
    if (not match or raw.hostname != 'raw.githubusercontent.com' or len(pieces) < 4
            or [s.lower() for s in pieces[:2]] != [s.lower() for s in match.groups()]):
        return doc, ['Lokaler Build benötigt einen GitHub-Repository-Link, keinen externen Compose-Link.']
    owner, repo = match.groups()
    commit = _github_json(f'https://api.github.com/repos/{owner}/{repo}/commits/{urllib.parse.quote(pieces[2], safe="")}')
    sha = commit.get('sha')
    if not isinstance(sha, str) or not _BUILD_SHA.fullmatch(sha):
        raise HTTPException(400, 'GitHub-Commit für den lokalen Build konnte nicht bestimmt werden.')
    path = '/'.join(pieces[3:])
    parent = posixpath.dirname(path) or '.'
    for name, svc in doc['services'].items():
        if 'build' in svc:
            # A published-looking tag does not prove the image exists; build the
            # exact publisher source whenever the Compose explicitly requests it.
            safe_tag = re.sub('[^a-z0-9-]', '-', f'{repo}-{name}'.lower()).strip('-')[:90]
            svc['image'] = f'installmonitor-local/{safe_tag}:{sha[:12]}'
    doc[_BUILD_META] = {'repository': project_url, 'revision': sha, 'compose_dir': parent}
    _validated_builds(doc)
    return doc, [f'Lokaler Docker-Build aus {project_url} vorbereitet (Commit {sha[:12]}).',
                 'Der Build erfolgt erst nach separater Bestätigung auf dem NAS. Der Quellcode/Dockerfile kann Befehle ausführen; bitte Herkunft prüfen.']




def _codeberg_branch_revision(project_url: str, branch: str) -> str:
    """Resolve a public Codeberg branch via Forgejo API or verified Git refs.

    Never silently substitute a moving branch for the commit: the later
    checkout must still match this exact 40-character object id.
    """
    match = _CODEBERG_REPO.fullmatch(project_url)
    if not match or not re.fullmatch(r'[A-Za-z0-9._-]{1,120}', branch) or branch in ('.', '..'):
        raise HTTPException(400, 'Ungültige Codeberg-Quelle oder Branch.')
    owner, project = match.groups()
    base = ('https://codeberg.org/api/v1/repos/' +
            urllib.parse.quote(owner, safe='') + '/' +
            urllib.parse.quote(project, safe=''))
    branch_name = urllib.parse.quote(branch, safe='')
    errors: list[str] = []
    # Forgejo exposes a commit object via either route. Some installations
    # restrict /commits/{ref} but permit /branches/{branch}.
    for kind in ('commits', 'branches'):
        try:
            payload = json.loads(_download_remote(
                f'{base}/{kind}/{branch_name}', max_bytes=250000))
            if kind == 'commits':
                sha = payload.get('sha') if isinstance(payload, dict) else None
            else:
                commit = payload.get('commit', {}) if isinstance(payload, dict) else {}
                sha = (commit.get('id') or commit.get('sha')) if isinstance(commit, dict) else None
            if isinstance(sha, str) and _BUILD_SHA.fullmatch(sha):
                return sha
            errors.append(kind + ': keine gültige Revision')
        except (HTTPException, ValueError, TypeError) as exc:
            # Don't expose a raw upstream error or tokens in a UI message.
            status = exc.status_code if isinstance(exc, HTTPException) else 502
            errors.append(f'{kind}: HTTP/JSON-Fehler ({status})')

    remote = f'https://codeberg.org/{owner}/{project}.git'
    ref = f'refs/heads/{branch}'
    env = os.environ.copy()
    env.update({
        'GIT_TERMINAL_PROMPT': '0',
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_ALLOW_PROTOCOL': 'https',
        'GIT_ASKPASS': '',
        'GIT_SSH_COMMAND': 'false',
    })
    try:
        response = subprocess.run(
            ['git', '-c', 'credential.helper=', '-c', 'core.hooksPath=/dev/null',
             '-c', 'protocol.file.allow=never', 'ls-remote', '--exit-code', remote, ref],
            capture_output=True, text=True, env=env, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(503,
            'Codeberg-Commit konnte weder über die API noch über Git HTTPS verifiziert werden. '
            'Git/DNS/HTTPS-Verbindung im Install-Monitor-Container prüfen. '
            + ', '.join(errors)) from exc
    if response.returncode == 0:
        for line in response.stdout.splitlines():
            fields = line.split('\t')
            if len(fields) == 2 and fields[1] == ref and _BUILD_SHA.fullmatch(fields[0]):
                return fields[0]
    raise HTTPException(503,
        'Codeberg-Commit weder über Forgejo API noch git ls-remote verifizierbar. '
        'Kein unsicherer Build gestartet. Git/HTTPS-Verbindung am NAS prüfen. '
        + ', '.join(errors))



def _attach_codeberg_build_context(doc: dict, project_url: str, resolved_url: str,
                                   original_compose: str) -> tuple[dict, list[str]]:
    """Pin a Codeberg build to an immutable Forgejo commit before installation."""
    match = _CODEBERG_REPO.fullmatch(project_url)
    raw = urllib.parse.urlsplit(resolved_url)
    parts = [urllib.parse.unquote(piece) for piece in raw.path.strip('/').split('/')]
    if (not match or raw.hostname != 'codeberg.org' or len(parts) < 6
            or parts[:2] != list(match.groups()) or parts[2:4] != ['raw', 'branch']):
        return doc, ['Codeberg-Build benötigt einen geprüften Codeberg-Projektlink mit Compose-Datei aus einem Branch.']
    owner, repo = match.groups()
    branch = parts[4]
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,120}', branch) or branch in ('.', '..'):
        raise HTTPException(400, 'Codeberg-Build-Branch ist ungültig oder wird nicht unterstützt.')
    sha = _codeberg_branch_revision(project_url, branch)
    path = '/'.join(parts[5:])
    if not _safe_github_index_path(path):
        raise HTTPException(400, 'Ungültiger Codeberg-Compose-Dateipfad.')
    pinned_url = (f'https://codeberg.org/{owner}/{repo}/raw/commit/{sha}/' +
                  '/'.join(urllib.parse.quote(part, safe='') for part in parts[5:]))
    pinned_compose = _download_remote(pinned_url)
    if pinned_compose != original_compose:
        raise HTTPException(409, 'Die Codeberg-Compose hat sich während der Analyse verändert. '
                            'Quelle erneut analysieren; kein Build aus einem anderen Commit.')
    parent = posixpath.dirname(path) or '.'
    for name, svc in doc['services'].items():
        if 'build' in svc:
            safe_tag = re.sub('[^a-z0-9-]', '-', f'{repo}-{name}'.lower()).strip('-')[:90]
            svc['image'] = f'installmonitor-local/{safe_tag}:{sha[:12]}'
    doc[_CODEBERG_BUILD_META] = {'repository': project_url, 'revision': sha,
                                'branch': branch, 'compose_dir': parent}
    _validated_builds(doc)
    return doc, [f'Codeberg-Docker-Build aus {project_url} vorbereitet (Commit {sha[:12]}).',
                 'Ein lokales Image aus der Original-Compose wird nicht als öffentlich verfügbares Image vorausgesetzt.',
                 'Git-LFS-Dateien werden beim NAS-Build einbezogen. Fremder Dockerfile-Code '
                 'wird erst nach deiner ausdrücklichen Bestätigung ausgeführt.']



def _archive_build_tree(repo: str, revision: str, destination: Path) -> Path:
    """Download pinned public GitHub snapshot with strict limits and no link/path traversal."""
    match = _BUILD_REPO.fullmatch(repo)
    if not match or not _BUILD_SHA.fullmatch(revision):
        raise HTTPException(400, 'Unsichere GitHub-Quelle für den Docker-Build.')
    owner, project = match.groups()
    url = f'https://codeload.github.com/{owner}/{project}/zip/{revision}'
    request = urllib.request.Request(url, headers={'User-Agent': 'InstallMonitor/0.1.32'})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            # Bound compressed source size before attempting to unzip.
            raw = response.read(32 * 1024 * 1024 + 1)
            if len(raw) > 32 * 1024 * 1024:
                raise HTTPException(400, 'GitHub-Projektarchiv ist größer als 32 MB. Bitte Image manuell bauen.')
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPException(502, 'GitHub-Quellarchiv für lokalen Build nicht abrufbar.') from exc
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            files = archive.infolist()
            if len(files) > 6000 or sum(i.file_size for i in files) > 160 * 1024 * 1024:
                raise HTTPException(400, 'GitHub-Build-Kontext überschreitet Sicherheitslimits.')
            root_names = {i.filename.split('/')[0] for i in files}
            if len(root_names) != 1:
                raise HTTPException(400, 'Unerwartete GitHub-Archivstruktur.')
            root = next(iter(root_names))
            if not root:
                raise HTTPException(400, 'Leeres GitHub-Archiv.')
            for entry in files:
                path = entry.filename.rstrip('/')
                pieces = path.split('/')
                mode = (entry.external_attr >> 16)
                if (not path or pieces[0] != root or any(x in ('', '.', '..') for x in pieces)
                        or path.startswith('/') or '\\' in path or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))):
                    raise HTTPException(400, 'Unsicherer Datei- oder Symlink-Eintrag im GitHub-Archiv.')
                if entry.is_dir():
                    (destination / Path(*pieces[1:])).mkdir(parents=True, exist_ok=True)
                elif len(pieces) > 1:
                    target = destination / Path(*pieces[1:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry) as inp, target.open('wb') as dst:
                        import shutil
                        shutil.copyfileobj(inp, dst)
    except (zipfile.BadZipFile, OSError) as exc:
        raise HTTPException(400, 'GitHub-Quellarchiv ist beschädigt oder kann nicht entpackt werden.') from exc
    return destination



def _archive_codeberg_tree(repo: str, branch: str, revision: str, destination: Path) -> Path:
    """Obtain a pinned Codeberg checkout including bounded Git LFS files.

    Only the exact public Codeberg repository is cloned; no submodules, hooks
    or external build scripts are executed by this source-acquisition step.
    Git LFS is pinned to the canonical same-repository endpoint so an
    untrusted .lfsconfig cannot switch downloads to private network hosts.
    """
    match = _CODEBERG_REPO.fullmatch(repo)
    if (not match or not _BUILD_SHA.fullmatch(revision)
            or not re.fullmatch(r'[A-Za-z0-9._-]{1,120}', branch)
            or branch in ('.', '..')):
        raise HTTPException(400, 'Codeberg-Buildquelle oder Commit ungültig.')
    owner, project = match.groups()
    remote = f'https://codeberg.org/{owner}/{project}.git'
    lfs_endpoint = remote + '/info/lfs'
    env = os.environ.copy()
    env.update({
        'GIT_TERMINAL_PROMPT': '0',
        'GIT_LFS_SKIP_SMUDGE': '1',
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_ALLOW_PROTOCOL': 'https',
        'GIT_LFS_FORCE_PROGRESS': '0',
    })
    def git(arguments: list[str], timeout: int = 180) -> str:
        try:
            result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *arguments],
                                    env=env, capture_output=True, text=True,
                                    timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(502, 'Codeberg-Git/Git-LFS ist nicht verfügbar oder hat das Zeitlimit überschritten.') from exc
        if result.returncode:
            raise HTTPException(502, 'Codeberg-Quellcode oder Git-LFS-Dateien konnten nicht abgerufen werden. Git-/LFS-Verbindung am NAS prüfen.')
        return result.stdout

    git(['clone', '--depth=1', '--single-branch', '--no-tags', '--no-checkout',
         '--branch', branch, remote, str(destination)], 240)
    if git(['-C', str(destination), 'rev-parse', 'HEAD']).strip() != revision:
        raise HTTPException(409, 'Der Codeberg-Branch wurde seit der Analyse verändert. Quelle erneut analysieren; kein Build ausgeführt.')
    git(['-C', str(destination), 'checkout', '--force', revision], 120)

    def measure() -> tuple[int, int]:
        count = total = 0
        for current, dirs, files in os.walk(destination, followlinks=False):
            if any((Path(current) / name).is_symlink() for name in dirs):
                raise HTTPException(400, 'Codeberg-Quellcode enthält einen symbolischen Verzeichnislink. Build aus Sicherheitsgründen abgebrochen.')
            if '.git' in dirs:
                # Count git objects too, but do not inspect Git's internal tree.
                gitdir = Path(current) / '.git'
                count += 1
                for directory, _, filenames in os.walk(gitdir, followlinks=False):
                    for filename in filenames:
                        path = Path(directory) / filename
                        total += path.lstat().st_size
                        if total > 512 * 1024 * 1024:
                            raise HTTPException(400, 'Codeberg-Git-Daten überschreiten 512 MB.')
                dirs.remove('.git')
            for filename in files:
                item = Path(current) / filename
                if item.is_symlink():
                    raise HTTPException(400, 'Codeberg-Quellcode enthält einen symbolischen Dateilink. Build aus Sicherheitsgründen abgebrochen.')
                count += 1
                total += item.lstat().st_size
                if count > 12000 or total > 512 * 1024 * 1024:
                    raise HTTPException(400, 'Codeberg-Build-Kontext überschreitet Sicherheitslimits (12.000 Dateien oder 512 MB).')
        return count, total

    files_before, size_before = measure()
    if size_before > 160 * 1024 * 1024:
        raise HTTPException(400, 'Codeberg-Quellcode ist ohne LFS bereits größer als 160 MB.')
    names = git(['-C', str(destination), 'lfs', 'ls-files', '--name-only'], 30).splitlines()
    if len(names) > 2500:
        raise HTTPException(400, 'Codeberg-Projekt enthält zu viele Git-LFS-Dateien.')
    lfs_size = 0
    for name in names:
        if (not _safe_github_index_path(name)
                or any(ord(c) < 32 for c in name)):
            raise HTTPException(400, 'Unsicherer Git-LFS-Dateipfad.')
        path = destination / name
        if not path.is_file() or path.is_symlink():
            raise HTTPException(400, 'Git-LFS-Datei oder Pointer fehlt im ausgecheckten Quellcode.')
        with path.open('rb') as stream:
            pointer = stream.read(512)
        match_size = re.search(rb'(?m)^size (\d+)$', pointer)
        if not pointer.startswith(b'version https://git-lfs.github.com/spec/v1\n') or not match_size:
            raise HTTPException(400, 'Git-LFS-Datei hat keinen gültigen Größen-Pointer.')
        lfs_size += int(match_size.group(1))
        if lfs_size > 256 * 1024 * 1024:
            raise HTTPException(400, 'Codeberg-Git-LFS-Daten überschreiten 256 MB. Bitte Image manuell bauen.')
    if names:
        git(['-C', str(destination), '-c', f'lfs.url={lfs_endpoint}',
             'lfs', 'pull', 'origin'], 300)
        for name in names:
            path = destination / name
            if not path.is_file() or path.is_symlink():
                raise HTTPException(400, 'Git-LFS-Checkout nach dem Download unvollständig.')
            with path.open('rb') as stream:
                prefix = stream.read(64)
            if prefix.startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise HTTPException(400, 'Git-LFS-Pointer blieb unaufgelöst. Kein Docker-Build gestartet.')
    measure()
    return destination



def _build_local_images(doc: dict, job_id: str) -> None:
    specs = _validated_builds(doc)
    if not specs:
        return
    provider = specs[0].get('provider', 'github')
    with tempfile.TemporaryDirectory(prefix='im-source-build-') as work:
        target = Path(work) / 'source'
        if provider == 'codeberg':
            tree = _archive_codeberg_tree(specs[0]['repo'], specs[0]['branch'],
                                          specs[0]['revision'], target)
        else:
            target.mkdir()
            tree = _archive_build_tree(specs[0]['repo'], specs[0]['revision'], target)
        for spec in specs:
            if local_image_available(spec['image']):
                _job_update(job_id, events=f"{spec['service']}: geprüftes lokales Image bereits vorhanden.")
                continue
            context = tree / spec['context']
            dockerfile = context / spec['dockerfile']
            if not context.is_dir() or not dockerfile.is_file() or dockerfile.is_symlink():
                raise HTTPException(400, f"{spec['service']}: Dockerfile oder Build-Kontext im geprüften {spec['provider']}-Commit nicht gefunden.")
            _job_update(job_id, phase='build', message=f"Baue {spec['service']} aus {spec['provider']}-Quellcode auf dem NAS.",
                        events=f"Docker-Build {spec['service']} · Commit {spec['revision'][:12]} begonnen.")
            cmd = ['docker', 'build', '--pull', '--tag', spec['image'], '--file', str(dockerfile)]
            if spec['target']:
                cmd += ['--target', spec['target']]
            for item in spec['args']:
                cmd += ['--build-arg', item]
            for item in spec['cache_from']:
                cmd += ['--cache-from', item]
            cmd += [str(context)]
            try:
                output = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                        text=True, timeout=900, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise HTTPException(502, f"{spec['service']}: Docker-Build fehlgeschlagen oder Zeitlimit erreicht.") from exc
            if output.returncode or not local_image_available(spec['image']):
                # Build logs may contain third-party instructions/secrets. Keep only a generic failure.
                raise HTTPException(502, f"{spec['service']}: Lokaler Docker-Build fehlgeschlagen. Bitte Docker-Build-Logs am NAS prüfen.")
            _job_update(job_id, events=f"{spec['service']}: Docker-Image {spec['image']} erfolgreich erstellt.")


def _zimaos_compose(doc: dict) -> str:
    # ZimaOS accepts images only. Locally built source is never shipped as a build key.
    sanitized = yaml.safe_load(yaml.safe_dump(doc))
    _validated_builds(sanitized)
    sanitized.pop(_BUILD_META, None)
    sanitized.pop(_CODEBERG_BUILD_META, None)
    sanitized.pop(_DOC_IMAGE_PREFLIGHT, None)
    for svc in sanitized['services'].values():
        if 'build' in svc:
            svc.pop('build')
            svc['pull_policy'] = 'never'
    return yaml.safe_dump(sanitized, allow_unicode=True, sort_keys=False, default_flow_style=False)

# Local-only images cannot be installed through the standard ZimaOS API: the
# ZimaOS image orchestrator always attempts a registry pull. Instead of an
# unmanaged `docker compose up` (which has no native dashboard tile), push the
# image to a loopback-only, persistent registry and use the official ZimaOS API.
# No host Docker daemon configuration is modified. The registry needs to remain
# available so ZimaOS can pull again when re-creating the managed app.
_LOCAL_REGISTRY_ADDRESS = '127.0.0.1:50813'
_LOCAL_REGISTRY_CONTAINER = 'install-monitor-local-registry'
_LOCAL_REGISTRY_IMAGE = 'registry:2.8.3'
_LOCAL_REGISTRY_DATA = '/DATA/AppData/Install-Monitor/registry'


def _verify_documented_images(doc: dict, job_id: str) -> None:
    """Fail closed on unverified publisher-doc images before POSTing to ZimaOS.

    A successful Docker-Hub documentation lookup is not proof of a published
    image; some publishers conditionally upload their images. Docker's manifest
    command fetches registry metadata without pulling image layers, starting
    containers or touching the ZimaOS app manager. Only documentation-fallback
    plans opt in: unchanged Compose imports preserve their previous behavior.
    """
    if doc.get(_DOC_IMAGE_PREFLIGHT) is not True:
        return
    images = sorted({str(svc['image']) for svc in doc['services'].values()
                     if isinstance(svc, dict) and isinstance(svc.get('image'), str)
                     and not str(svc['image']).startswith('installmonitor-local/')})
    if not images:
        raise HTTPException(400, 'Die Docker-Anleitung enthält keine öffentlich prüfbaren Images.')
    for image in images:
        _job_update(job_id, phase='preflight',
                    message=f'Prüfe veröffentlichtes Docker-Image: {image}',
                    events=f'Image-Manifest wird geprüft: {image}')
        try:
            result = subprocess.run(['docker', 'manifest', 'inspect', image],
                                    capture_output=True, text=True,
                                    timeout=30, check=False)
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(503, f"{image}: Registry-Prüfung hat zu lange gedauert. Keine ZimaOS-App erstellt; später erneut versuchen.") from exc
        except OSError as exc:
            raise HTTPException(503, f"{image}: Docker-Manifestprüfung nicht verfügbar. Keine ZimaOS-App erstellt.") from exc
        if result.returncode:
            # Do not display arbitrary registry text: it can contain secrets,
            # tokens or untrusted diagnostic content. Give an actionable result.
            error = (result.stderr + '\n' + result.stdout).lower()[:6000]
            unavailable = ('denied', 'unauthorized', 'authentication required',
                           'access forbidden', 'pull access denied',
                           'manifest unknown', 'manifest not found',
                           'name unknown', 'repository does not exist',
                           'not found')
            if any(token in error for token in unavailable):
                raise HTTPException(424, f"{image}: Docker-Image ist unter diesem Tag nicht öffentlich abrufbar oder benötigt Anmeldung. Die Dokumentation nennt es, aber die Registry liefert kein Manifest. Installation vor ZimaOS-Registrierung gestoppt; anderen verfügbaren Image-Tag wählen.")
            raise HTTPException(503, f"{image}: Docker-Registry konnte nicht zuverlässig geprüft werden. Keine ZimaOS-App angelegt; Netzwerk und Registry-Zugang prüfen.")
        _job_update(job_id, events=f'Veröffentlichtes Docker-Image bestätigt: {image}')


def _uses_private_local_images(doc: dict) -> bool:
    if any('build' in svc for svc in doc['services'].values()):
        _validated_builds(doc)
    local_images = [str(svc.get('image', '')) for svc in doc['services'].values()
                    if str(svc.get('image', '')).startswith('installmonitor-local/')]
    for image_name in local_images:
        if not _BUILD_IMG.fullmatch(image_name):
            raise HTTPException(400, 'Ungültiger lokaler Install-Monitor-Image-Tag.')
    return bool(local_images)


def _run_docker_guarded(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess:
    """Run only fixed Docker subcommands; never forward raw errors or secrets."""
    try:
        response = subprocess.run(['docker', *args], capture_output=True, text=True,
                                  timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(502, 'Lokale Docker-Registry konnte nicht vorbereitet werden.') from exc
    if response.returncode != 0:
        raise HTTPException(502, 'Lokale Docker-Registry ist nicht bereit. Docker-Status auf dem NAS prüfen.')
    return response


def _ensure_private_registry() -> None:
    """Require the registry service from the *same* install-monitor Compose project.

    Never create an unrelated standalone registry. A one-time migration moves
    old registry storage under /DATA/AppData/Install-Monitor/registry.
    """
    try:
        examine = subprocess.run(['docker', 'container', 'inspect', _LOCAL_REGISTRY_CONTAINER],
                                 capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(502, 'Install-Monitor-Registry konnte nicht geprüft werden.') from exc
    if examine.returncode != 0:
        raise HTTPException(503, 'Install-Monitor-Registry fehlt. Bitte die gemeinsame Install-Monitor-Compose-Konfiguration starten.')
    try:
        state = json.loads(examine.stdout)[0]
        port = state['HostConfig']['PortBindings']['5000/tcp']
        mounts = state.get('Mounts', [])
        expected = any(v.get('Type') == 'bind' and
                       v.get('Source') == _LOCAL_REGISTRY_DATA and
                       v.get('Destination') == '/var/lib/registry' for v in mounts)
        labels = state.get('Config', {}).get('Labels') or {}
        valid = (state['Config']['Image'] == _LOCAL_REGISTRY_IMAGE
                 and port == [{'HostIp': '127.0.0.1', 'HostPort': '50813'}]
                 and expected
                 and labels.get('com.docker.compose.project') == 'install-monitor'
                 and labels.get('com.docker.compose.service') == 'registry')
    except (KeyError, ValueError, TypeError, IndexError):
        valid = False
    if not valid:
        raise HTTPException(409, 'Die Registry ist nicht Teil von Install-Monitor oder verwendet einen anderen Speicherort. Bitte Migration abschließen; vorhandene Container bleiben unberührt.')
    if not state.get('State', {}).get('Running'):
        _run_docker_guarded(['start', _LOCAL_REGISTRY_CONTAINER], timeout=30)
    for _ in range(20):
        try:
            with urllib.request.urlopen('http://' + _LOCAL_REGISTRY_ADDRESS + '/v2/', timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.25)
    raise HTTPException(502, 'Die interne Install-Monitor-Registry ist nicht erreichbar. ZimaOS-Installation wurde nicht gestartet.')

def _publish_local_images(doc: dict, job_id: str) -> dict:
    """Make self-built images pullable by ZimaOS without exposing registry to LAN."""
    output = yaml.safe_load(yaml.safe_dump(doc))
    expected = [(service, cfg.get('image')) for service, cfg in output['services'].items()
                if str(cfg.get('image', '')).startswith('installmonitor-local/')]
    if not expected:
        return output
    for service, source in expected:
        if not _BUILD_IMG.fullmatch(source) or not local_image_available(source):
            raise HTTPException(502, f'{service}: Lokal gebautes Image nicht vorhanden.')
    _job_update(job_id, phase='submitted', message='Lokale Registry für ZimaOS wird vorbereitet.',
                events='Privates Image wird für die reguläre ZimaOS-App-Installation bereitgestellt.')
    _ensure_private_registry()
    for service, source in expected:
        image_tail = source.split('/', 1)[1]
        target = _LOCAL_REGISTRY_ADDRESS + '/installmonitor/' + image_tail
        if not IMAGE.fullmatch(target):
            raise HTTPException(400, f'{service}: Ungültiger Registry-Image-Name.')
        _job_update(job_id, message=f'{service}: Lokales Image wird ZimaOS bereitgestellt.',
                    events=f'{service}: Lokales Registry-Image wird übertragen.')
        _run_docker_guarded(['tag', source, target], timeout=20)
        _run_docker_guarded(['push', target], timeout=300)
        # Actual Docker pull roundtrip catches unsupported localhost registries
        # *before* installing an app with the ZimaOS API.
        _run_docker_guarded(['pull', target], timeout=120)
        output['services'][service]['image'] = target
        output['services'][service].pop('build', None)
        output['services'][service].pop('pull_policy', None)
        _job_update(job_id, events=f'{service}: Image ist über die NAS-interne Registry abrufbar.')
    return output


# v0.2.17: determine the HOST timezone, never assume the container's TZ
# equals ZimaOS. The host probe is read-only, no network, no privileges.
_TZ_CACHE: dict[str, Any] = {'at': 0.0, 'value': '', 'error': ''}
_TZ_LOCK = threading.RLock()
_TZ_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_+.-]*(?:/[A-Za-z0-9_+.-]+){0,4}$')
_COMMON_ZONES = ('Europe/Berlin', 'Europe/London', 'Europe/Lisbon', 'UTC', 'Etc/UTC',
                 'America/New_York', 'America/Los_Angeles', 'America/Sao_Paulo',
                 'Asia/Tokyo', 'Asia/Dubai', 'Australia/Sydney')
_TZ_HOST_PROBE = r"""
import os, re, json
value = ''
try:
    with open('/im-host-etc/timezone', 'r', encoding='utf-8') as f:
        value = f.read(120).strip()
except OSError:
    pass
if not value:
    try:
        dest = os.readlink('/im-host-etc/localtime')
        if '/zoneinfo/' in dest:
            value = dest.split('/zoneinfo/', 1)[1]
    except OSError:
        pass
if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_+.-]*(?:/[A-Za-z0-9_+.-]+){0,4}', value) or '..' in value:
    value = ''
print(json.dumps({'timezone': value}))
"""

def _valid_timezone(value: str) -> bool:
    if not isinstance(value, str) or not _TZ_PATTERN.fullmatch(value) or '..' in value:
        return False
    try:
        ZoneInfo(value)
        return True
    except ZoneInfoNotFoundError:
        # Container may lack tzdata. Accept only recognized names from
        # the local system if available, never arbitrary env payloads.
        return value in _COMMON_ZONES
    except (ValueError, OSError):
        return False

def _host_timezone(*, refresh: bool = False) -> tuple[str, str]:
    now = time.monotonic()
    with _TZ_LOCK:
        if not refresh and now - _TZ_CACHE['at'] < 600:
            return _TZ_CACHE['value'], _TZ_CACHE['error']
        result = ''
        error = 'NAS-Zeitzone nicht sicher erkannt. Bitte manuell wählen.'
        try:
            info = subprocess.run(['docker', 'inspect', 'install-monitor', '--format', '{{.Image}}'],
                                  capture_output=True, text=True, timeout=8, check=True)
            image_id = info.stdout.strip()
            if not re.fullmatch(r'sha256:[a-f0-9]{64}', image_id):
                raise ValueError('Docker-Image nicht verfügbar')
            cmd = ['docker','run','--rm','--network','none','--read-only',
                   '--cap-drop','ALL','--security-opt','no-new-privileges',
                   '--pids-limit','32','--memory','64m','--user','65534:65534',
                   '--mount','type=bind,source=/etc,target=/im-host-etc,readonly',
                   '--entrypoint','python',image_id,'-c',_TZ_HOST_PROBE]
            response = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=25, check=True)
            payload = json.loads(response.stdout)
            value = payload.get('timezone', '')
            if _valid_timezone(value):
                result, error = value, ''
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
                ValueError, TypeError, json.JSONDecodeError):
            pass
        _TZ_CACHE.update({'at': now, 'value': result, 'error': error})
        return result, error

def _timezone_map(doc: dict) -> dict[str, str]:
    # Do not modify Compose when inspecting.
    return {name: _get_service_environment(service, 'TZ')
            for name, service in doc['services'].items()
            if _get_service_environment(service, 'TZ')}

def _apply_timezone_choice(doc: dict, p: Plan, notes: list[str]) -> None:
    if p.timezone_mode == 'original':
        return
    if p.timezone_mode == 'nas':
        zone, error = _host_timezone()
        if not zone:
            notes.append('NAS-Zeitzone nicht ermittelbar; Hersteller-Zeitzone bleibt erhalten. '
                         'Bei Bedarf im Zeitzonenabschnitt manuell auswählen.')
            return
    else:
        zone = p.timezone_name.strip()
        if not _valid_timezone(zone):
            raise HTTPException(400, 'Ungültige Zeitzone. Bitte einen gültigen IANA-Namen wie Europe/Berlin wählen.')
    updated = 0
    for name, svc in doc['services'].items():
        env = svc.get('environment') or {}
        # TZ may be present with no value ("TZ:" or a list entry "TZ").
        present = ('TZ' in env if isinstance(env, dict) else
                   any(isinstance(item, str) and (item == 'TZ' or item.startswith('TZ='))
                       for item in env) if isinstance(env, list) else False)
        if present or p.timezone_add_missing:
            if isinstance(env, list) and 'TZ' in env:
                # Replace bare TZ instead of producing duplicate Compose keys.
                env[env.index('TZ')] = 'TZ=' + zone
            else:
                _set_service_environment(svc, 'TZ', zone)
            updated += 1
    if updated:
        notes.append('Zeitzone ' + zone + ' für ' + str(updated) + ' Dienst(e) gesetzt.' +
                     (' Auch bisher fehlende TZ-Variablen wurden auf Wunsch ergänzt.' if p.timezone_add_missing else ''))
    else:
        notes.append('Keine TZ-Variable im Original gefunden; ohne ausdrückliche Zustimmung wird keine ergänzt.')


@app.post('/api/timezone/inspect')
def inspect_timezone(req: Request, body: TimezoneLookup):
    require_write(req)
    doc = safe_yaml(body.source)
    zone, error = _host_timezone()
    try:
        choices = sorted(available_timezones())
    except (OSError, ValueError):
        choices = []
    choices = sorted(set(choices).union(_COMMON_ZONES))
    return {'host_timezone': zone, 'host_detected': bool(zone), 'warning': error,
            'original': _timezone_map(doc), 'timezones': choices}


def build_plan(p: Plan) -> dict:
    name = slug(p.name)
    data = safe_yaml(p.source)
    preparation_notes: list[str] = []
    setup_options = _setup_later_options(data, p.selected_profiles)
    allowed_later = {option['profile'] for option in setup_options}
    if len(set(p.setup_later_profiles)) != len(p.setup_later_profiles) or not set(p.setup_later_profiles).issubset(allowed_later):
        raise HTTPException(400, 'Spätere Einrichtung nur für ausgewählte Cloudflare-/Tailscale-Dienste möglich.')
    if p.tailscale_auth_key and 'tailscale' not in p.selected_profiles:
        raise HTTPException(400, 'Tailscale-Schlüssel übermittelt, obwohl das Profil nicht ausgewählt ist.')
    if p.cloudflare_tunnel_token and 'tunnel' not in p.selected_profiles:
        raise HTTPException(400, 'Cloudflare-Token übermittelt, obwohl das Profil nicht ausgewählt ist.')
    active_profiles, deferred_profiles = defer_missing_local_builds(data, p.selected_profiles, preparation_notes)
    select_profiles(data, active_profiles, preparation_notes)
    _apply_resource_choices(data, p.resources, preparation_notes, target_system=p.target_system)
    _apply_timezone_choice(data, p, preparation_notes)
    _normalize_legacy_env_files(data, preparation_notes)
    for option in setup_options:
        profile, service_name = option['profile'], option['service']
        if profile in p.setup_later_profiles and service_name in data['services']:
            _set_setup_later(data['services'][service_name], profile)
            preparation_notes.append(f'{service_name}: Wird mitinstalliert; Einrichtung ausdrücklich für später vorgemerkt. Der Container kann bis zur Konfiguration stoppen oder neu starten.')
    for service_name, service in data['services'].items():
        image = str(service.get('image', '')).lower()
        if 'tailscale/tailscale' in image:
            if p.tailscale_auth_key.strip():
                _set_service_environment(service, 'TS_AUTHKEY', p.tailscale_auth_key.strip())
            preparation_notes.append(f'{service_name}: Tailscale benötigt /dev/net/tun sowie die vom Original vorgesehenen Berechtigungen.')
        if 'cloudflare/cloudflared' in image:
            if p.cloudflare_tunnel_token.strip():
                _set_service_environment(service, 'TUNNEL_TOKEN', p.cloudflare_tunnel_token.strip())
            preparation_notes.append(f'{service_name}: Öffentliche Hostnamen und die Route zum Dienst müssen im Cloudflare-Tunnel konfiguriert sein.')
    unresolved = _unresolved_runtime_variables(data)
    if unresolved:
        raise HTTPException(400, 'Noch offene Compose-Variablen: ' + ', '.join(sorted(unresolved)) + '. Bitte die Werte im Quell-Compose ergänzen.')
    # An explicitly selected Meilisearch search profile needs a strong key.
    # In the upstream Compose this key defaults to an empty string, which
    # makes the optional service exit immediately when the profile is selected.
    for service_name, service in data['services'].items():
        if str(service.get('image', '')).startswith('getmeili/meilisearch:') and not _get_service_environment(service, 'MEILI_MASTER_KEY'):
            key = secrets.token_hex(32)
            _set_service_environment(service, 'MEILI_MASTER_KEY', key)
            preparation_notes.append(f'{service_name}: Meilisearch-Schlüssel generiert. Die fertige Compose-Konfiguration mit dem Schlüssel sicher aufbewahren.')
    # Existing locally built images need no second build or GitHub download.
    for service_name, service in data['services'].items():
        if 'build' in service and isinstance(service.get('image'), str) and local_image_available(service['image']):
            service.pop('build')
            preparation_notes.append(f"{service_name}: Bereits vorhandenes lokales Docker-Image wird verwendet.")
    activation_errors: list[str] = []
    if data.get('x-install-monitor-review-required'):
        has_deployment_data = any(
            bool(s.get('ports') or s.get('volumes') or s.get('network_mode') == 'host')
            for s in data['services'].values()
        )
        if not has_deployment_data:
            activation_errors.append(
                'Unvollständiger Image-Entwurf: Ports und Speicherpfade wurden nicht verifiziert. '
                'Offizielle Compose-Datei verwenden oder die benötigten Angaben manuell ergänzen.'
            )
    activation_errors.extend(_app_url_issues(data))
    activation_errors.extend(_project_image_issues(data, name))
    empty_secrets = _required_credentials(data)
    for svc_name, key in empty_secrets:
        activation_errors.append(f'{svc_name}: {key} fehlt. Bitte unter Zugangsdaten vergeben oder sicher erzeugen.')
    if any('build' in svc for svc in data['services'].values()):
        try:
            specs = _validated_builds(data)
            for item in specs:
                preparation_notes.append(f"{item['service']}: {item['provider']}-Quellcode (Commit {item['revision'][:12]}) wird auf dem NAS gebaut. Das Image wird nicht durch ein fremdes oder altes Image ersetzt.")
        except HTTPException as exc:
            activation_errors.append(str(exc.detail))
    root = (p.data_dir.strip().rstrip("/") or f"/DATA/AppData/{name}")
    if not root.startswith(("/DATA/", "/media/")) or ".." in root.split("/") or not re.fullmatch(r"/[a-zA-Z0-9_./ -]{1,499}", root):
        raise HTTPException(400, "Der Datenordner muss unter /DATA/ oder /media/ liegen.")
    # Silo's shipped default /opt/silo is a host storage path. The user has
    # explicitly selected the app-data base in this wizard; keep the upstream
    # per-service directory layout under that base, not in the host OS root.
    is_silo = any('ghcr.io/silo-server/silo-server' in str(x.get('image', '')).lower()
                  for x in data['services'].values())
    if is_silo:
        mapped = 0
        for service in data['services'].values():
            volumes = service.get('volumes') or []
            for i, mount in enumerate(volumes):
                if isinstance(mount, str) and mount.startswith('/opt/silo/') and ':' in mount:
                    volumes[i] = root + '/' + mount[len('/opt/silo/'):]
                    mapped += 1
                elif isinstance(mount, dict) and str(mount.get('source','')).startswith('/opt/silo/'):
                    mount['source'] = root + '/' + str(mount['source'])[len('/opt/silo/'):]
                    mapped += 1
        if mapped:
            preparation_notes.append(f'Silo: {mapped} Standard-Datenpfade von /opt/silo nach {root} verlegt.')
    # Covers saved or directly pasted DSM Compose sources even when the
    # source-analysis wizard step was bypassed.
    synology_notes = _im_convert_synology_binds(data, name, root)
    preparation_notes.extend(synology_notes)
    preparation_notes.extend(_im_wordpress_network_references(data))
    if synology_notes:
        preparation_notes.extend(_im_wordpress_dependency_cleanup(data))
    _convert_volumes(data, name, root)
    if any(isinstance(vol, str) and vol.split(':', 1)[0] in (data.get('volumes') or {})
           or isinstance(vol, dict) and vol.get('type') == 'volume'
           for svc in data['services'].values() for vol in (svc.get('volumes') or [])):
        preparation_notes.append('Benannte Docker-Volumes bleiben unverändert (einschließlich gemeinsamer Nutzung, Docker-Rechte und :ro). Sie liegen im Docker-Volume-Speicher, nicht automatisch unter dem gewählten AppData-Ordner.')
    # Re-check on the exact converted YAML sent to ZimaOS, not only on the
    # upstream source. Only issues of the final compose block installation.
    data["name"] = name
    for issue in _setup_issues(data) + _im_host_file_mount_issues(data) + _im_unconverted_synology_binds(data) + _im_wordpress_credentials_issues(data) + _im_wordpress_weak_password_issues(data):
        if issue not in activation_errors:
            activation_errors.append(issue)
    data["name"] = name
    infrastructure = ("postgres", "redis", "mysql", "mariadb", "mongo", "valkey", "rabbitmq", "meilisearch", "pgvector", "timescale")
    # Multi-service stacks can expose a *support* container (e.g. Watchtower
    # 10444) while the real UI service uses `network_mode: host` (Scrypted
    # HTTPS 10443). Honor the publisher's explicit x-casaos.main before any
    # heuristic. Never redirect the ZimaOS tile to a helper service.
    upstream_casa = data.get('x-casaos')
    explicit_main = upstream_casa.get('main') if isinstance(upstream_casa, dict) else None
    if isinstance(explicit_main, str) and explicit_main in data['services']:
        main = explicit_main
    else:
        main = next((k for k, v in data["services"].items()
                     if v.get("ports") and k.lower() not in infrastructure
                     and not any(t in str(v.get("image", "")).lower() for t in infrastructure)), None)
        if main is None:
            main = next((k for k, v in data["services"].items() if v.get("ports")), next(iter(data["services"])))
    svc = data["services"][main]
    published = ""
    for port in svc.get("ports", []) or []:
        if isinstance(port, str):
            parts = port.split(":")
            if len(parts) >= 2 and parts[-2].isdigit():
                published = parts[-2]
                break
        elif isinstance(port, dict):
            published = str(port.get("published", ""))
            break
    if not published and svc.get('network_mode') == 'host':
        documented_port = _declared_host_network_port(data, main)
        if documented_port is None:
            image = str(svc.get('image', '')).lower()
            if image.startswith('ghcr.io/music-assistant/server:') or image == 'ghcr.io/music-assistant/server':
                documented_port = 8095
        if documented_port is not None:
            published = str(documented_port)  # ZimaOS WebUI entry; never adds Compose ports.
    icon = p.icon.strip() or "https://cdn.jsdelivr.net/gh/selfhst/icons/svg/docker.svg"
    if not icon.startswith("https://") and not icon.startswith("http://"):
        raise HTTPException(400, "Das Icon benötigt eine gültige HTTP(S)-Adresse.")
    if p.category not in ("AI", "Developer", "Finance", "Home", "Media", "Networking", "Others", "Productivity", "Social"):
        raise HTTPException(400, "Ungültige Kategorie.")
    # Keep author-provided ZimaOS metadata, including descriptions, tips,
    # developer and architecture declarations. Override only the fields the
    # user explicitly edits or which must follow a changed host port.
    upstream = data.get('x-casaos')
    casa = dict(upstream) if isinstance(upstream, dict) else {}
    casa['main'] = main
    casa['port_map'] = str(published)
    casa.setdefault('index', '/')
    casa.setdefault('scheme', 'http')
    casa.setdefault('store_app_id', name)
    casa['icon'] = icon
    # Compose ignores x-casaos, whereas container inventory tools read Docker
    # labels. A stale upstream service label can otherwise display the icon of
    # an entirely different application (e.g. Home Assistant for ZimaBrain CE).
    if p.icon.strip():
        labels = svc.get('labels')
        if labels is None:
            labels = {}
        elif isinstance(labels, list):
            # Preserve all non-icon labels, translating the standard list format.
            parsed = {}
            for label in labels:
                if not isinstance(label, str):
                    raise HTTPException(400, f'{main}: Ungültiger Docker-Label-Eintrag.')
                key, sep, value = label.partition('=')
                if not key:
                    raise HTTPException(400, f'{main}: Leerer Docker-Label-Name.')
                parsed[key] = value if sep else ''
            labels = parsed
        elif not isinstance(labels, dict):
            raise HTTPException(400, f'{main}: Ungültiger Docker-Labels-Block.')
        labels['icon'] = icon
        # x-casaos is authoritative for dashboard metadata; labels.icon is the
        # matching fallback for Update Monitor and other Docker inventory tools.
        svc['labels'] = labels
    title = dict(casa.get('title')) if isinstance(casa.get('title'), dict) else {}
    title['custom'] = p.title.strip()
    casa['title'] = title
    casa['category'] = p.category
    casa.setdefault('id', f'local.installmonitor.{name}')
    casa.setdefault('architectures', ['amd64', 'arm64'])
    data['x-casaos'] = casa
    contract_errors, contract_warnings = _im_zimaos_contract_checks(data)
    contract_warnings.extend(_im_credential_mismatch_warnings(data))
    for binding in _im_network_bindings(data):
        if binding['exposure'] == 'loopback':
            contract_warnings.append(f"{binding['service']}: Host-Port {binding['host_port']} ist nur auf dem NAS erreichbar (127.0.0.1). Für Zugriff aus dem LAN unter App-Adresse und Netzwerk bewusst freigeben.")
    for issue in contract_errors:
        if issue not in activation_errors:
            activation_errors.append(issue)
    report = require_ports_free(data)
    notes = preparation_notes + _warnings(data) + contract_warnings
    if data.get(_DOC_IMAGE_PREFLIGHT) is True:
        notes.append('Vor dem Installieren werden die Docker-Images aus der Herausgeber-Anleitung per Registry-Manifest überprüft. Scheitert die Prüfung, wird keine ZimaOS-App angelegt.')
    if any(str(svc.get('image', '')).startswith('installmonitor-local/') for svc in data['services'].values()):
        notes.append('Lokales Docker-Image: Install Monitor baut die App auf dem NAS und stellt das Image über eine Registry nur auf 127.0.0.1 bereit. Die App selbst wird über ZimaOS installiert, damit die Dashboard-Kachel angelegt werden kann.')
    templates = _im_wordpress_ini_templates(data, name)
    if templates:
        notes.append('WordPress: uploads.ini wird nur bei fehlender Datei mit dokumentierten PHP-Upload-Grenzen unter /DATA/AppData erstellt. Vorhandene Dateien werden nicht überschrieben.')
    managed = _managed_host_directories(data, name)
    if managed:
        notes.append('Vor Installation werden diese App-Datenordner auf dem NAS geprüft und bei Bedarf erstellt: ' + ', '.join(managed))
    if report["ports"]:
        notes.append("Host-Ports unmittelbar vor dieser Vorschau geprüft; beim Installieren erfolgt eine erneute Prüfung.")
    if any(svc.get('network_mode') == 'host' for svc in data['services'].values()):
        notes.append('Host-Netzwerk: Der dokumentierte Web-Port wird auf Belegung geprüft. Weitere vom Dienst verwendete NAS-Ports können unbekannt bleiben. Bei Konflikten kann der Host-Port nicht über Docker umgeleitet werden.')
    if not published:
        notes.append("Kein Web-Port gefunden: Die App kann ohne Web-Oberfläche starten")
    # Structured remediation actions let the UI target exactly the missing
    # requirement without interpreting or altering the original Compose.
    # The server-side /api/install check remains the final authority.
    setup_actions = []
    for error in activation_errors:
        service_name = error.split(':', 1)[0]
        if 'Tailscale-Schlüssel fehlt' in error:
            kind = 'tailscale_auth'
        elif 'Cloudflare Tunnel benötigt' in error:
            kind = 'cloudflare_auth'
        elif 'Projekt-Image' in error or 'lokale Image' in error or 'Original-Build' in error:
            kind = 'source_image'
        else:
            kind = 'source_compose'
        setup_actions.append({'service': service_name, 'kind': kind})
    if p.target_system != 'zimaos':
        # Export-only profiles do not invoke the ZimaOS app-management API.
        # Standard Compose has no CasaOS application metadata.
        if p.target_system == 'docker':
            data.pop('x-casaos', None)
        activation_errors.append('Nur Compose-Export: ' + ('CasaOS' if p.target_system == 'casaos' else 'Standard Docker') + ' ist derzeit kein ZimaOS-Installationsziel.')
        notes.append('Dieses Zielprofil kann als YAML heruntergeladen werden. Direkte Installation wird nicht freigegeben.')
    compose = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return {"compose": compose, "services": list(data["services"]), "notes": notes, "main": main, "port": published,
            "setup_later_profiles": p.setup_later_profiles, "setup_later_options": setup_options,
            "deferred_profiles": deferred_profiles, "active_profiles": active_profiles,
            "install_ready": not activation_errors, "setup_issues": activation_errors,
            "setup_actions": setup_actions}


def api_call(host: str, path: str, method: str, token: str = "", payload: str = "", content_type: str = "application/json") -> tuple[int, str]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = token  # ZimaOS expects raw JWT, not 'Bearer JWT'
    data = payload.encode("utf-8") if method in ("POST", "PUT") else None
    if data is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(host + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=20) as res:
            return res.status, res.read(350000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(1200).decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        raise HTTPException(502, f"ZimaOS nicht erreichbar: {str(exc.reason)[:140]}") from exc


def zima_login(host: str, username: str, password: str) -> str:
    status, raw = api_call(host, "/v1/users/login", "POST", payload=json.dumps({"username": username, "password": password}))
    if status != 200:
        raise HTTPException(401, f"ZimaOS-Anmeldung abgelehnt (HTTP {status}).")
    try:
        return json.loads(raw)["data"]["token"]["access_token"]
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(502, "Unerwartete Login-Antwort von ZimaOS.") from exc


@app.get("/")
def index():
    # Keep package release label aligned when distributing only main.py.
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = re.sub(r"Install Monitor v[0-9]+(?:\.[0-9]+){2}(?:-beta\.\d+|-preview)?", "Install Monitor v" + VERSION, html)
    # Query-string versions must follow the deployed backend. A stale app.js
    # otherwise hides newly added installation fields despite a newer UI label.
    html = re.sub(r"(/static/(?:app\.js|style\.css)\?v=)[A-Za-z0-9._-]+",
                  lambda match: match.group(1) + VERSION, html)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.get("/logo.svg")
def logo():
    return FileResponse(STATIC / "logo.svg", media_type="image/svg+xml")



# Container resource sampling based on Update Monitor v0.3.420.
_IM_ABOUT_STARTED = time.time()

def _im_read_cgroup(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None

def _im_cpu_seconds():
    raw = _im_read_cgroup('/sys/fs/cgroup/cpu.stat')
    if raw:
        for line in raw.splitlines():
            parts=line.split()
            if len(parts)==2 and parts[0]=='usage_usec':
                try: return int(parts[1])/1_000_000.0
                except ValueError: pass
    raw=_im_read_cgroup('/sys/fs/cgroup/cpuacct/cpuacct.usage')
    if raw:
        try: return int(raw)/1_000_000_000.0
        except ValueError: pass
    return None

def _im_memory_bytes():
    for path in ('/sys/fs/cgroup/memory.current','/sys/fs/cgroup/memory/memory.usage_in_bytes'):
        raw=_im_read_cgroup(path)
        if raw is not None:
            try: return int(raw)
            except ValueError: pass
    return None

def _im_zimaos_app_management():
    # The same ZimaOS marker as Update Monitor. No invented positive result.
    marker=Path('/host/run/casaos/app-management.url')
    try:
        if marker.is_file():
            return bool(marker.read_text(encoding='utf-8').strip())
        # Without the host mount the detection has not been performed.
        return False if Path('/host/run/casaos').is_dir() else None
    except OSError:
        return None

@app.get('/api/about')
def im_about(req: Request):
    require_auth(req)
    first=_im_cpu_seconds()
    start=time.perf_counter()
    if first is not None:
        time.sleep(0.12)
    second=_im_cpu_seconds()
    duration=time.perf_counter()-start
    cpu=(round(max(0.0,100.0*(second-first)/duration),1)
         if first is not None and second is not None and duration>0 else None)
    memory=_im_memory_bytes()
    return {
        'version':VERSION,
        'cpu_percent':cpu,
        'memory_mb':round(memory/(1024*1024),1) if memory is not None else None,
        'started_at':int(_IM_ABOUT_STARTED),
        'zimaos_app_management':_im_zimaos_app_management(),
    }

@app.get("/api/session")
def session(req: Request):
    return {"authenticated": bool(req.session.get("authenticated")), "csrf": req.session.get("csrf", "") if req.session.get("authenticated") else "", "version": VERSION}


@app.post("/api/login")
def login(req: Request, body: Login):
    # Rate limit by client, independent of the submitted username, to make
    # it harder to enumerate user accounts. Always verify the password too.
    key = req.client.host if req.client else "unknown"
    fails = LOGINS.get(key, 0)
    if fails >= 20:
        raise HTTPException(429, "Zu viele Anmeldeversuche. Container neu starten oder später erneut versuchen.")
    username_valid = hmac.compare_digest(body.username.encode('utf-8'), ADMIN_USER.encode('utf-8'))
    password_valid = _admin_password_valid(body.password)
    if not (username_valid and password_valid):
        LOGINS[key] = fails + 1
        raise HTTPException(401, "Benutzername oder Passwort ungültig.")
    LOGINS.pop(key, None)
    req.session.clear()
    req.session["authenticated"] = True
    req.session["csrf"] = secrets.token_urlsafe(32)
    return {"ok": True, "csrf": req.session["csrf"]}


@app.post("/api/logout")
def logout(req: Request):
    require_write(req)
    req.session.clear()
    return {"ok": True}


# Host hardware detection. The Install Monitor container normally has no /dev/dri
# mapping, so checking its own /sys is unreliable. Probe the NAS via a constrained
# one-shot copy of the *existing local* Install Monitor Python image; no network,
# host root or privileged mode is needed. Only fixed sysfs identifiers and
# /dev/dri node existence/ownership are read. No third-party image is pulled.
_HARDWARE_LOCK = threading.RLock()
_HARDWARE_CACHE: dict[str, Any] = {'at': 0.0, 'result': None}
_HOST_GPU_PROBE = r'''
import json, os
from pathlib import Path
s=Path('/im-host-sys'); d=Path('/im-host-dev/dri')
known={'0x1002':'amd','0x8086':'intel','0x10de':'nvidia'}
found={}
for p in (s/'bus/pci/devices').glob('*'):
    try:
        v=(p/'vendor').read_text().strip().lower()
        klass=(p/'class').read_text().strip().lower()
        if v in known and klass.startswith('0x03'):
            k=known[v]; f=found.setdefault(k, {'vendor':k, 'device_ids':[]})
            device=(p/'device').read_text().strip()
            if device not in f['device_ids']: f['device_ids'].append(device)
    except (OSError, ValueError): pass
render=[]
for p in sorted((s/'class/drm').glob('renderD*')):
    try:
        v=(p/'device/vendor').read_text().strip().lower()
        if v not in known: continue
        dev=d/p.name
        if not dev.exists() or not dev.is_char_device(): continue
        st=dev.stat()
        render.append({'vendor':known[v], 'node':'/dev/dri/'+p.name, 'gid':st.st_gid})
    except (OSError, ValueError): pass
print(json.dumps({'gpus':list(found.values()), 'render':render}))
'''


def _host_memory_mb() -> int | None:
    try:
        raw=Path('/proc/meminfo').read_text()
        value=re.search(r'^MemTotal:\s*(\d+)\s+kB', raw, re.M)
        return int(value.group(1))//1024 if value else None
    except (OSError, ValueError):
        return None


def _probe_host_hardware(*, refresh: bool = False) -> dict:
    now=time.monotonic()
    with _HARDWARE_LOCK:
        if not refresh and _HARDWARE_CACHE.get('result') and now-_HARDWARE_CACHE['at'] < 90:
            return _HARDWARE_CACHE['result']
    cpu=os.cpu_count()
    hardware: dict[str, Any] = {
        'cpu_threads': cpu if isinstance(cpu,int) and cpu>0 else None,
        'memory_mb': _host_memory_mb(),
        'gpus': [], 'probe_ok': False, 'warning': '', 'nvidia_runtime': False,
    }
    try:
        info=subprocess.run(['docker','info','--format','{{json .Runtimes}}'],
                            timeout=8,capture_output=True,text=True,check=True)
        runtimes=json.loads(info.stdout)
        hardware['nvidia_runtime']=isinstance(runtimes,dict) and 'nvidia' in runtimes
        systeminfo=subprocess.run(['docker','info','--format','{{.MemTotal}} {{.NCPU}}'],
                                  timeout=8,capture_output=True,text=True,check=True)
        numbers=systeminfo.stdout.strip().split()
        if len(numbers)==2 and all(x.isdigit() for x in numbers):
            hardware['memory_mb']=int(numbers[0])//(1024*1024)
            hardware['cpu_threads']=int(numbers[1])
        inspected=subprocess.run(['docker','inspect','install-monitor','--format','{{.Image}}'],
                                  timeout=8,capture_output=True,text=True,check=True)
        image=inspected.stdout.strip()
        if not re.fullmatch(r'sha256:[a-f0-9]{64}',image):
            raise RuntimeError('Lokales Install-Monitor-Image nicht ermittelbar.')
        cmd=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
             '--security-opt','no-new-privileges','--pids-limit','64','--memory','96m',
             '--user','65534:65534',
             '--mount','type=bind,source=/sys,target=/im-host-sys,readonly',
             '--mount','type=bind,source=/dev,target=/im-host-dev,readonly',
             '--entrypoint','python',image,'-c',_HOST_GPU_PROBE]
        probe=subprocess.run(cmd,timeout=25,capture_output=True,text=True,check=True)
        response=json.loads(probe.stdout)
        scanned=response.get('gpus',[])
        render=response.get('render',[])
        if not isinstance(scanned,list) or not isinstance(render,list):
            raise ValueError('Ungültige GPU-Hardwareantwort')
        hardware['probe_ok']=True
        for record in scanned:
            vendor=record.get('vendor')
            if vendor not in ('amd','intel','nvidia'): continue
            device_nodes=[r for r in render if r.get('vendor')==vendor]
            usable=(bool(device_nodes) if vendor!='nvidia' else hardware['nvidia_runtime'])
            reason=('NVIDIA Container Runtime erkannt' if usable and vendor=='nvidia' else
                    '/dev/dri-Rendergerät erkannt' if usable else
                    'NVIDIA Container Toolkit / Docker Runtime fehlt' if vendor=='nvidia' else
                    'Kein nutzbares /dev/dri-Rendergerät gefunden')
            hardware['gpus'].append({'vendor':vendor,'name':{'amd':'AMD','intel':'Intel','nvidia':'NVIDIA'}[vendor],
                                     'device_ids':record.get('device_ids',[])[:6],
                                     'render_nodes':[r['node'] for r in device_nodes],
                                     'render_groups':sorted({r['gid'] for r in device_nodes}),
                                     'available':bool(usable), 'reason':reason})
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        hardware['warning']='GPU-Erkennung über den Docker-Host nicht verfügbar. Kein GPU-Zugriff ohne bestätigte Hardware.'
    with _HARDWARE_LOCK:
        _HARDWARE_CACHE.update({'at':now,'result':hardware})
    return hardware


@app.get('/api/hardware')
def host_hardware(req: Request, refresh: bool = False):
    require_auth(req)
    return _probe_host_hardware(refresh=refresh)


def _apply_resource_choices(doc: dict, chosen: dict[str, ServiceResources], notes: list[str], *, target_system: str = "zimaos") -> None:
    if not chosen: return
    if len(chosen) > 64 or not set(chosen).issubset(set(doc['services'])):
        raise HTTPException(400,'Unbekannte Dienste in der Ressourcen-Konfiguration.')
    needs_hw=any(x.memory_mb is not None or x.cpu_cores is not None or x.gpu!='none' for x in chosen.values())
    hw=_probe_host_hardware() if needs_hw else {}
    threads=hw.get('cpu_threads') or os.cpu_count() or 1
    mem=hw.get('memory_mb')
    for name, limits in chosen.items():
        svc=doc['services'][name]
        if limits.memory_mb is not None:
            if mem and limits.memory_mb > mem:
                raise HTTPException(400,f'{name}: RAM-Limit übersteigt den NAS-Arbeitsspeicher ({mem} MB).')
            if target_system in ('zimaos','casaos'):
                # ZimaOS/CasaOS editor uses deploy.resources.limits. Only
                # modify limits explicitly chosen by the user. Other deploy
                # attributes (including reservations) and cpu_shares survive.
                deploy=svc.setdefault('deploy',{})
                if not isinstance(deploy,dict):
                    raise HTTPException(400,f'{name}: Ungültiger ursprünglicher deploy-Block.')
                resources=deploy.setdefault('resources',{})
                if not isinstance(resources,dict):
                    raise HTTPException(400,f'{name}: Ungültiger ursprünglicher resources-Block.')
                dest=resources.setdefault('limits',{})
                if not isinstance(dest,dict):
                    raise HTTPException(400,f'{name}: Ungültiger ursprünglicher limits-Block.')
                dest['memory']=f'{limits.memory_mb}MB'
                svc.pop('mem_limit',None)  # Avoid two conflicting RAM limits.
            else:
                svc['mem_limit']=f'{limits.memory_mb}m'
                deploy=svc.get('deploy')
                if isinstance(deploy,dict) and isinstance(deploy.get('resources'),dict):
                    lim=deploy['resources'].get('limits')
                    if isinstance(lim,dict) and 'memory' in lim:
                        lim['memory']=f'{limits.memory_mb}MB'
            notes.append(f'{name}: RAM-Limit {limits.memory_mb} MB.')
        if limits.cpu_cores is not None:
            if limits.cpu_cores > threads:
                raise HTTPException(400,f'{name}: CPU-Limit ({limits.cpu_cores}) größer als {threads} logische NAS-CPUs.')
            if target_system in ('zimaos','casaos'):
                deploy=svc.setdefault('deploy',{})
                if not isinstance(deploy,dict):
                    raise HTTPException(400,f'{name}: Ungültiger ursprünglicher deploy-Block.')
                resources=deploy.setdefault('resources',{})
                if not isinstance(resources,dict):
                    raise HTTPException(400,f'{name}: Ungültiger ursprünglicher resources-Block.')
                dest=resources.setdefault('limits',{})
                if not isinstance(dest,dict):
                    raise HTTPException(400,f'{name}: Ungültiger ursprünglicher limits-Block.')
                dest['cpus']=str(limits.cpu_cores)
                svc.pop('cpus',None)
            else:
                svc['cpus']=limits.cpu_cores
                deploy=svc.get('deploy')
                if isinstance(deploy,dict) and isinstance(deploy.get('resources'),dict):
                    lim=deploy['resources'].get('limits')
                    if isinstance(lim,dict) and 'cpus' in lim:
                        lim['cpus']=str(limits.cpu_cores)
            notes.append(f'{name}: CPU-Limit {limits.cpu_cores} logische CPUs.')
        if limits.gpu!='none':
            if not hw.get('probe_ok'):
                raise HTTPException(400,'NAS-Grafikhardware konnte nicht sicher erkannt werden; GPU-Zuweisung verweigert.')
            gpu=next((x for x in hw['gpus'] if x['vendor']==limits.gpu and x['available']),None)
            if not gpu:
                raise HTTPException(400,f'{name}: {limits.gpu.upper()}-Beschleunigung auf diesem NAS nicht verfügbar.')
            if limits.gpu in ('amd','intel'):
                existing=svc.get('devices') or []
                if not isinstance(existing,list):
                    raise HTTPException(400,f'{name}: Gerätezuweisungen im Original-Compose sind ungültig.')
                if not any(isinstance(x,str) and x.startswith('/dev/dri:') for x in existing):
                    existing.append('/dev/dri:/dev/dri')
                svc['devices']=existing
                group_add=svc.get('group_add') or []
                if not isinstance(group_add,list):
                    raise HTTPException(400,f'{name}: Gruppen im Original-Compose sind ungültig.')
                for group in gpu.get('render_groups',[]):
                    if str(group) not in {str(g) for g in group_add}:
                        group_add.append(str(group))
                if group_add: svc['group_add']=group_add
                notes.append(f'{name}: {limits.gpu.upper()}-Rendergerät /dev/dri freigegeben (VAAPI nur bei App-Unterstützung).')
            else:
                if svc.get('runtime') not in (None,'nvidia'):
                    raise HTTPException(400,f'{name}: Vorhandene Container-Runtime darf nicht überschrieben werden.')
                svc['runtime']='nvidia'
                if not _get_service_environment(svc,'NVIDIA_VISIBLE_DEVICES'):
                    _set_service_environment(svc,'NVIDIA_VISIBLE_DEVICES','all')
                if not _get_service_environment(svc,'NVIDIA_DRIVER_CAPABILITIES'):
                    _set_service_environment(svc,'NVIDIA_DRIVER_CAPABILITIES','compute,video,utility')
                notes.append(f'{name}: NVIDIA-Runtime aktiviert; Anwendung benötigt eigene CUDA/NVENC-Konfiguration.')
            doc.setdefault('x-install-monitor-gpu-requests',{})[name]=limits.gpu
            notes.append(f'{name}: GPU-Nutzung ausdrücklich ausgewählt. Vor Installation App-Treiber prüfen.')


def _validate_gpu_access_at_install(doc: dict) -> None:
    requests=doc.get('x-install-monitor-gpu-requests')
    if not isinstance(requests,dict) or not requests:return
    needs_dri=any(x in ('amd','intel') for x in requests.values())
    needs_nvidia=any(x=='nvidia' for x in requests.values())
    for name, vendor in requests.items():
        svc=doc['services'].get(name)
        if not isinstance(svc,dict) or vendor not in ('amd','intel','nvidia'):
            raise HTTPException(400,'GPU-Dienstangabe in der Compose-Vorschau ist ungültig.')
        if vendor in ('amd','intel') and not any(isinstance(v,str) and v.startswith('/dev/dri:') for v in (svc.get('devices') or [])):
            raise HTTPException(400,f'{name}: /dev/dri-Freigabe fehlt in der GPU-Konfiguration.')
        if vendor=='nvidia' and svc.get('runtime')!='nvidia':
            raise HTTPException(400,f'{name}: NVIDIA-Runtime fehlt in der GPU-Konfiguration.')
    if not (needs_dri or needs_nvidia):return
    hw=_probe_host_hardware(refresh=True)
    if not hw.get('probe_ok'):
        raise HTTPException(400,'Grafikhardware vor Installation nicht verifizierbar. Kein automatischer GPU-Zugriff.')
    if needs_dri and not any(g['available'] and g['vendor'] in ('amd','intel') for g in hw['gpus']):
        raise HTTPException(400,'/dev/dri ist am NAS nicht als nutzbares Rendergerät verfügbar.')
    if needs_nvidia and not any(g['available'] and g['vendor']=='nvidia' for g in hw['gpus']):
        raise HTTPException(400,'NVIDIA-Runtime/GPU am NAS nicht betriebsbereit.')


@app.get("/api/host")
def host(req: Request):
    require_auth(req)
    try:
        out = subprocess.run(["docker", "ps", "-a", "--format", "{{json .}}"], check=True, timeout=8, capture_output=True, text=True)
        containers = [json.loads(s) for s in out.stdout.splitlines() if s.strip()][:250]
        return {"docker": True, "containers": containers}
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return {"docker": False, "containers": [], "notice": "Docker-Socket nicht erreichbar."}




# v0.2.14: Read-only selfh.st application discovery. The project publishes a
# compact directory of software, not verified Docker installation manifests.
# Never synthesize Compose files or images from directory entries.
_SELFHST_APPS_SOURCES = (
    'https://selfhst.github.io/cdn/directory/software.json',
    'https://raw.githubusercontent.com/selfhst/cdn/main/directory/software.json',
)
_SELFHST_APPS_CACHE: dict[str, Any] = {'expires': 0.0, 'items': [], 'source': ''}
_SELFHST_APPS_LOCK = threading.Lock()
_SELFHST_APPS_ICON = re.compile(r'^[a-z0-9][a-z0-9_-]{1,90}$')


def _selfhst_apps_safe_url(value: Any) -> str:
    if not isinstance(value, str):
        return ''
    candidate = value.strip()
    if not candidate or any(ord(c) < 33 for c in candidate):
        return ''
    if candidate.startswith(('github.com/', 'gitlab.com/', 'codeberg.org/')):
        candidate = 'https://' + candidate
    elif candidate.startswith(('www.',)):
        candidate = 'https://' + candidate
    elif '://' not in candidate:
        candidate = 'https://' + candidate
    try:
        parsed = urllib.parse.urlsplit(candidate)
    except ValueError:
        return ''
    if (parsed.scheme not in ('https', 'http') or not parsed.hostname
        or parsed.username or parsed.password or '.' not in parsed.hostname
        or ':' in parsed.netloc or len(candidate) > 450):
        return ''
    return candidate


def _im_catalog_add_icons(items: list[dict], catalog: dict) -> None:
    """Attach verified selfh.st/icons assets for the app directory only.

    Names/slug references must exist in the official index. Unknown apps keep
    the initial-letter placeholder. Do not touch the user-facing icon picker.
    """
    for item in items:
        explicit = item.get('icon_ref')
        options = (explicit, item.get('slug'), _icon_key(item.get('name') or ''))
        match = next((catalog[key] for key in options
                      if isinstance(key, str) and key in catalog), None)
        if not isinstance(match, dict):
            continue
        reference = match.get('Reference')
        if not isinstance(reference, str) or not _ICON_SLUG_RE.fullmatch(reference):
            continue
        base = 'https://cdn.jsdelivr.net/gh/selfhst/icons/'
        if match.get('SVG') == 'Yes':
            item['icon_url'] = base + 'svg/' + reference + '.svg'
        elif match.get('PNG') == 'Yes':
            item['icon_url'] = base + 'png/' + reference + '.png'
        if match.get('PNG') == 'Yes':
            item['icon_png_url'] = base + 'png/' + reference + '.png'


def _selfhst_apps_from_rows(data: Any) -> list[dict]:
    if not isinstance(data, list):
        raise ValueError('Ungültiges Verzeichnisformat')
    entries: list[dict] = []
    seen: set[str] = set()
    for row in data:
        if not isinstance(row, list) or len(row) < 17:
            continue
        title, ref = row[1], row[2]
        if not isinstance(title, str) or not isinstance(ref, str):
            continue
        title, ref = title.strip()[:110], ref.strip().lower()
        # Keep unusual upstream rows too. In the Oct 2026 catalog one
        # project's slug is a complete GitHub URL, not an icon-safe slug.
        # This directory is for display, never executable source code.
        if not _SELFHST_APPS_ICON.fullmatch(ref):
            parsed = urllib.parse.urlsplit(ref)
            if parsed.scheme == 'https' and parsed.hostname == 'github.com':
                ref = parsed.path.rstrip('/').rsplit('/', 1)[-1].lower()
            if not _SELFHST_APPS_ICON.fullmatch(ref):
                ref = re.sub(r'[^a-z0-9_-]+', '-', title.lower()).strip('-')[:90]
        if not title or not _SELFHST_APPS_ICON.fullmatch(ref) or ref in seen:
            continue
        seen.add(ref)
        website = _selfhst_apps_safe_url(row[3])
        repo = _selfhst_apps_safe_url(row[4])
        source = str(row[6] or '')[:48]
        description = str(row[5] or '')[:420]
        icon_ref = str(row[10] or '').strip().lower() if len(row)>10 else ''
        icon_url = ('https://cdn.jsdelivr.net/gh/selfhst/icons/png/' + icon_ref + '.png'
                    if _SELFHST_APPS_ICON.fullmatch(icon_ref) else '')
        stars = row[13] if len(row)>13 else 0
        try:
            stars = max(0, min(100_000_000, int(stars)))
        except (ValueError, TypeError):
            stars = 0
        updated = row[15] if len(row)>15 else ''
        updated = updated[:10] if isinstance(updated, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}.*', updated) else ''
        tag_ids = row[17] if len(row)>17 else []
        tag_ids = [x for x in tag_ids if isinstance(x, int) and 0 <= x <= 10000][:24] if isinstance(tag_ids, list) else []
        entries.append({'name':title,'slug':ref,'description':description,'website':website,
                        'repository':repo,'source':source,'icon_url':icon_url,
                        'stars':stars,'updated':updated,'tag_ids':tag_ids,
                        'catalog_id':int(row[0]) if str(row[0]).isdigit() else 0,
                        'new_rank':int(row[20]) if len(row)>20 and str(row[20]).isdigit() else 0,
                        'icon_ref':icon_ref if _SELFHST_APPS_ICON.fullmatch(icon_ref) else ''})
    if not entries:
        raise ValueError('Keine gültigen Einträge erhalten')
    return entries


def _selfhst_apps() -> tuple[list[dict], str, bool]:
    now = time.monotonic()
    with _SELFHST_APPS_LOCK:
        if _SELFHST_APPS_CACHE['expires'] > now and _SELFHST_APPS_CACHE['items']:
            return _SELFHST_APPS_CACHE['items'], _SELFHST_APPS_CACHE['source'], False
    last_error: Exception | None = None
    for url in _SELFHST_APPS_SOURCES:
        try:
            request = urllib.request.Request(url, headers={
                'Accept':'application/json','User-Agent':'InstallMonitor/0.2.14 (selfhst catalog)'})
            with urllib.request.urlopen(request, timeout=14) as response:
                raw = response.read(2_500_001)
            if len(raw) > 2_500_000:
                raise ValueError('App-Katalog überschreitet das Größenlimit')
            entries = _selfhst_apps_from_rows(json.loads(raw.decode('utf-8')))
        except (urllib.error.URLError, TimeoutError, ValueError, TypeError,
                UnicodeDecodeError, OSError) as exc:
            last_error = exc
            continue
        # Tags are an independent, optional public index. A tag-service outage
        # must never prevent browsing the application directory.
        tagmap: dict[int, str] = {}
        for tags_url in (
                'https://selfhst.github.io/cdn/directory/tags.json',
                'https://raw.githubusercontent.com/selfhst/cdn/main/directory/tags.json'):
            try:
                tag_request = urllib.request.Request(tags_url, headers={
                    'Accept':'application/json','User-Agent':'InstallMonitor/0.2.14 (selfhst catalog)'})
                with urllib.request.urlopen(tag_request, timeout=7) as response:
                    tag_bytes=response.read(90_001)
                if len(tag_bytes)>90_000: raise ValueError('Tags zu groß')
                tag_data=json.loads(tag_bytes.decode('utf-8'))
                if not isinstance(tag_data,list): raise ValueError('Tags ungültig')
                tagmap={int(row[0]):str(row[1])[:75] for row in tag_data
                        if isinstance(row,list) and len(row)>1 and isinstance(row[0],int)
                        and isinstance(row[1],str) and row[1]}
                break
            except (urllib.error.URLError, TimeoutError, ValueError, UnicodeDecodeError, OSError):
                continue
        for entry in entries:
            entry['tags']=[tagmap[key] for key in entry.pop('tag_ids') if key in tagmap][:12]
        # The app directory and the independent icon repository may update at
        # different times. Icon lookup failure must not hide any app entry.
        try:
            icon_index, _ = _selfhst_index()
            _im_catalog_add_icons(entries, icon_index)
        except (OSError, ValueError, TypeError):
            pass
        with _SELFHST_APPS_LOCK:
            _SELFHST_APPS_CACHE.update({'expires':time.monotonic()+3600,
                                       'items':entries,'source':url})
        return entries, url, False
    with _SELFHST_APPS_LOCK:
        if _SELFHST_APPS_CACHE['items']:
            return _SELFHST_APPS_CACHE['items'], _SELFHST_APPS_CACHE['source'], True
    raise HTTPException(503, 'selfh.st-App-Katalog derzeit nicht erreichbar: '
                        + str(last_error or 'Netzwerkfehler')[:160])


@app.get('/api/selfhst/apps')
def selfhst_apps(req: Request):
    require_auth(req)
    entries, source_url, stale = _selfhst_apps()
    return {'apps':entries,'source':source_url,'count':len(entries),
            'stale':stale,'cache_minutes':60,'discovery_only':True}

# v0.2.21: Open catalog lookup beyond the selfh.st curated directory.
# All locally indexed selfh.st entries are retained. On a user's search the
# separate GitHub API adds public repositories, whether or not selfh.st lists
# them. Discovery does NOT mean a usable Docker image or valid Compose exists.
_GITHUB_APP_SEARCH_CACHE: dict[tuple[str, int], tuple[float, dict]] = {}
_GITHUB_APP_SEARCH_LOCK = threading.Lock()
_GITHUB_APP_SEARCH_TTL_SECONDS = 600
_GITHUB_APP_SEARCH_QUERY = re.compile(r"[^\w .-]", re.UNICODE)


def _github_catalog_normalize_query(value: str) -> str:
    term = str(value or '').strip()
    # Search accepts an explicitly entered GitHub repository link, too.
    if term.startswith('https://github.com/'):
        parts = urllib.parse.urlsplit(term)
        segments = parts.path.strip('/').split('/')
        if (parts.hostname == 'github.com' and not parts.username and
                not parts.password and len(segments) == 2 and
                all(GITHUB_PART.fullmatch(part) for part in segments)):
            return '/'.join(segments)
    term = _GITHUB_APP_SEARCH_QUERY.sub(' ', term)
    term = ' '.join(term.split())[:80]
    if len(term) < 2:
        raise HTTPException(400, 'Für die GitHub-Suche mindestens zwei Zeichen eingeben.')
    return term


def _github_catalog_result(raw: dict) -> dict:
    full_name = str(raw.get('full_name') or '')[:203]
    pathparts = full_name.split('/')
    if (len(pathparts) != 2 or not all(GITHUB_PART.fullmatch(part) for part in pathparts)
            or raw.get('private') is True):
        return {}
    repo = 'https://github.com/' + full_name
    updated = str(raw.get('pushed_at') or raw.get('updated_at') or '')[:10]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', updated):
        updated = ''
    description = str(raw.get('description') or '')[:420]
    stars = raw.get('stargazers_count', 0)
    try: stars = max(0, min(int(stars), 100_000_000))
    except (TypeError, ValueError): stars = 0
    result = {'name':str(raw.get('name') or pathparts[1])[:110],
            'slug':full_name.lower(), 'description':description,
            'website':_selfhst_apps_safe_url(raw.get('homepage')),
            'repository':repo,'source':'GitHub','provider':'github',
            'icon_url':'','stars':stars,'updated':updated,
            'created':str(raw.get('created_at') or '')[:10],'tags':['GitHub'],
            'archived':bool(raw.get('archived')),
            'fork':bool(raw.get('fork')),
            'owner':pathparts[0]}
    # Use the already cached icon index; do not fetch the entire icon catalog
    # for every individual GitHub result or slow down repository searches.
    icons = _SELFHST_INDEX_CACHE.get('entries') or {}
    if icons:
        result['icon_ref'] = _icon_key(pathparts[1])
        _im_catalog_add_icons([result], icons)
    return result


def _github_catalog_search(term: str, page: int) -> dict:
    now = time.monotonic()
    cachekey = (term.casefold(), page)
    with _GITHUB_APP_SEARCH_LOCK:
        record = _GITHUB_APP_SEARCH_CACHE.get(cachekey)
        if record and record[0] > now:
            return record[1]
    # Query syntax is constructed server-side; don't allow callers to inject
    # GitHub search qualifiers or cause a query for private repositories.
    exactrepo = re.fullmatch(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}', term)
    if exactrepo:
        try:
            result = _github_catalog_result(_github_json('https://api.github.com/repos/' + term))
        except HTTPException as exc:
            if 'HTTP 404' not in str(exc.detail):
                raise
            result = {}
        payload = {'apps':[result] if result else [], 'total_count':1 if result else 0,
                   'page':1, 'has_more':False, 'incomplete':False, 'source':'GitHub'}
    else:
        words = ' '.join(term.split()[:7])
        # Do not filter archived, forked, or projects without a Dockerfile;
        # user must be able to see them and decide after source analysis.
        query = words + ' in:name,description,readme is:public'
        params = urllib.parse.urlencode({'q':query,'per_page':50,'page':page})
        response = _github_json('https://api.github.com/search/repositories?' + params)
        records = response.get('items')
        if not isinstance(records,list):
            raise HTTPException(502,'GitHub lieferte keine gültige Suchliste.')
        apps = [v for entry in records if isinstance(entry,dict)
                if (v := _github_catalog_result(entry))]
        try: count = max(0, int(response.get('total_count') or 0))
        except (TypeError, ValueError): count = len(apps)
        payload = {'apps':apps,'total_count':count,'page':page,
                   'has_more':page * 50 < min(1000,count),
                   'incomplete':bool(response.get('incomplete_results')),
                   'source':'GitHub'}
    with _GITHUB_APP_SEARCH_LOCK:
        if len(_GITHUB_APP_SEARCH_CACHE)>100:
            _GITHUB_APP_SEARCH_CACHE.clear()
        _GITHUB_APP_SEARCH_CACHE[cachekey] = (time.monotonic()+_GITHUB_APP_SEARCH_TTL_SECONDS,payload)
    return payload


@app.get('/api/apps/github-search')
def apps_github_search(req: Request, q: str = '', page: int = 1):
    require_auth(req)
    if len(q)>150 or page<1 or page>20:
        raise HTTPException(400, 'Ungültige GitHub-Suchanfrage oder Seitennummer.')
    term = _github_catalog_normalize_query(q)
    result = _github_catalog_search(term,page)
    return {**result,'query':term,'discovery_only':True,'page_size':50,
            'max_results_per_query':1000}


# v0.2.49: first-party iSanto1306 ZimaOS app-store source catalog.
# GitHub Pages is not a required dependency. Source Compose files are read from
# a fixed public GitHub repository; each is still analyzed by the existing
# standard source/import and preview paths before any installation.
_ISANTO_SOURCE_ROOT = 'https://github.com/isanto1306/zima-appstore'
_ISANTO_API = 'https://api.github.com/repos/isanto1306/zima-appstore/contents/Apps?ref=main'
_ISANTO_RAW_ROOT = 'https://raw.githubusercontent.com/isanto1306/zima-appstore/main/Apps'
_ISANTO_CATALOG_CACHE: dict[str, Any] = {'expires': 0.0, 'apps': [], 'origin': ''}
_ISANTO_CATALOG_LOCK = threading.RLock()
_ISANTO_APP_SEGMENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,55}$')
_ISANTO_CONFIRMED_TEMPLATES = ('DiskMonitor', 'UpdateMonitor')


def _isanto_title(value: Any, fallback: str) -> str:
    if isinstance(value, dict):
        value = value.get('de_DE') or value.get('en_US') or next(
            (x for x in value.values() if isinstance(x, str)), '')
    return str(value or fallback).strip()[:120]


# Additional short descriptions for the two first-party app templates.
# en_US/de_DE are read from the original ZimaOS Compose metadata whenever
# present; these translations fill the locale variants not yet in the repo.
_ISANTO_TAGLINE_TRANSLATIONS = {
    'DiskMonitor': {
        'fr_FR': 'Surveillance du stockage, de SMART et de l’activité des disques pour ZimaOS/Linux',
        'pt_PT': 'Monitorização de armazenamento, SMART e atividade dos discos para ZimaOS/Linux',
        'es_ES': 'Supervisión del almacenamiento, SMART y actividad de discos para ZimaOS/Linux',
    },
    'UpdateMonitor': {
        'fr_FR': 'Surveillance des mises à jour Docker, règles, sauvegardes et restauration pour ZimaOS',
        'pt_PT': 'Monitorização de atualizações Docker, políticas, cópias de segurança e restauro para ZimaOS',
        'es_ES': 'Supervisión de actualizaciones Docker, políticas, copias de seguridad y restauración para ZimaOS',
    },
}
_ISANTO_LOCALES = ('de_DE', 'en_US', 'fr_FR', 'pt_PT', 'es_ES')


def _isanto_localized_taglines(value: Any, name: str) -> dict[str, str]:
    """Keep authored locale strings and supplement only missing first-party ones.

    Unknown apps are not machine-translated; their original text remains
    available separately as `description` for an honest fallback.
    """
    translated: dict[str, str] = {}
    if isinstance(value, dict):
        for locale in _ISANTO_LOCALES:
            short = locale.split('_')[0]
            text_value = value.get(locale) or value.get(short)
            if isinstance(text_value, str) and text_value.strip():
                translated[locale] = text_value.strip()[:420]
    for locale, text_value in _ISANTO_TAGLINE_TRANSLATIONS.get(name, {}).items():
        translated.setdefault(locale, text_value)
    return translated


def _isanto_catalog() -> tuple[list[dict], str]:
    with _ISANTO_CATALOG_LOCK:
        if _ISANTO_CATALOG_CACHE['expires'] > time.monotonic() and _ISANTO_CATALOG_CACHE['apps']:
            return _ISANTO_CATALOG_CACHE['apps'], _ISANTO_CATALOG_CACHE['origin']
    origin = 'github-source'
    try:
        folders = json.loads(_download_remote(_ISANTO_API, max_bytes=180000))
        if not isinstance(folders, list):
            raise ValueError('GitHub lieferte keine App-Verzeichnisse')
        names = [str(x['name']) for x in folders if isinstance(x, dict)
                 and x.get('type') == 'dir' and isinstance(x.get('name'), str)
                 and _ISANTO_APP_SEGMENT.fullmatch(x['name'])][:40]
        if not names:
            raise ValueError('Keine Apps im Store-Verzeichnis gefunden')
    except (HTTPException, ValueError, KeyError, TypeError, json.JSONDecodeError):
        # These two paths were confirmed against the owner's GitHub repository
        # on 2026-10-17. Show as last-known-source paths, never as a successful
        # live refresh. The Analyze action still fetches the actual Compose.
        with _ISANTO_CATALOG_LOCK:
            if _ISANTO_CATALOG_CACHE['apps']:
                return _ISANTO_CATALOG_CACHE['apps'], 'cached'
        names = list(_ISANTO_CONFIRMED_TEMPLATES)
        origin = 'verified-fallback'
    apps: list[dict] = []
    for name in names:
        source_url = f'{_ISANTO_RAW_ROOT}/{name}/docker-compose.yml'
        try:
            content = _download_remote(source_url, max_bytes=160000)
            doc = yaml.safe_load(content)
            if not isinstance(doc, dict) or not isinstance(doc.get('services'), dict) or not doc['services']:
                continue
            casa = doc.get('x-casaos', {})
            if not isinstance(casa, dict):
                casa = {}
            first = next((x for x in doc['services'].values() if isinstance(x, dict)), {})
            labels = first.get('labels') if isinstance(first, dict) else None
            icon = (labels.get('icon', '') if isinstance(labels, dict) else '')
            if not icon:
                icon = casa.get('icon', '')
            if not isinstance(icon, str) or not icon.startswith('https://') or len(icon) > 800:
                icon = ''
            title = _isanto_title(casa.get('title'), re.sub(r'(?<!^)(?=[A-Z])', ' ', name))
            raw_description = casa.get('tagline') or casa.get('description')
            description = _isanto_title(raw_description,
                                        'ZimaOS Docker App – Original-Compose aus iSanto1306 Apps')
            description_i18n = _isanto_localized_taglines(raw_description, name)
            category = _isanto_title(casa.get('category'), 'Others')
            apps.append({'id': name, 'name': title, 'description': description,
                         'description_i18n': description_i18n,
                         'category': category, 'icon_url': icon,
                         'compose_url': source_url,
                         'source_url': f'{_ISANTO_SOURCE_ROOT}/blob/main/Apps/{name}/docker-compose.yml',
                         'store': 'iSanto1306 Apps'})
        except (HTTPException, ValueError, TypeError, yaml.YAMLError):
            if origin != 'verified-fallback':
                continue
    if not apps and origin == 'verified-fallback':
        # Clear stale fallback: paths are historical, not verified at present.
        for name in names:
            apps.append({'id': name, 'name': re.sub(r'(?<!^)(?=[A-Z])', ' ', name),
                         'description': 'Zuletzt bestätigter Compose-Pfad. Vor Verwendung prüfen.',
                         'description_i18n': {
                             'de_DE': 'Zuletzt bestätigter Compose-Pfad. Vor Verwendung prüfen.',
                             'en_US': 'Last confirmed Compose location. Verify before using.',
                             'fr_FR': 'Dernier emplacement Compose confirmé. À vérifier avant utilisation.',
                             'pt_PT': 'Último caminho Compose confirmado. Verifique antes de utilizar.',
                             'es_ES': 'Última ruta Compose confirmada. Compruébela antes de usarla.'},
                         'category': 'Others', 'icon_url': '',
                         'compose_url': f'{_ISANTO_RAW_ROOT}/{name}/docker-compose.yml',
                         'source_url': f'{_ISANTO_SOURCE_ROOT}/blob/main/Apps/{name}/docker-compose.yml',
                         'store': 'iSanto1306 Apps'})
    if not apps:
        raise HTTPException(503, 'Der iSanto1306 App-Store ist momentan nicht lesbar.')
    apps.sort(key=lambda x: x['name'].lower())
    with _ISANTO_CATALOG_LOCK:
        _ISANTO_CATALOG_CACHE.update({'expires': time.monotonic() + 900,
                                      'apps': apps, 'origin': origin})
    return apps, origin


@app.get('/api/app-stores/isanto1306')
def isanto_store_apps(req: Request):
    require_auth(req)
    apps, origin = _isanto_catalog()
    return {'apps': apps, 'source': _ISANTO_SOURCE_ROOT,
            'origin': origin, 'live': origin == 'github-source',
            'note': 'Jede App wird vor Installation separat analysiert; keine automatische Installation.'}


# Official LinuxServer.io catalog: read-only, server-side, cached. The publisher
# maintains the data at https://api.linuxserver.io/api/v1/images . No GitHub
# search/API token or external AI service is required.
_LSIO_URL = 'https://api.linuxserver.io/api/v1/images?include_config=true&include_deprecated=false'
_LSIO_CACHE: dict[str, Any] = {'expires': 0.0, 'images': {}}
_LSIO_LOCK = threading.Lock()
_LSIO_NAME = re.compile(r'^[a-z0-9][a-z0-9_.-]{1,75}$')


def _lsio_images() -> dict[str, dict]:
    now = time.monotonic()
    with _LSIO_LOCK:
        if _LSIO_CACHE['expires'] > now and _LSIO_CACHE['images']:
            return _LSIO_CACHE['images']
    try:
        request = urllib.request.Request(_LSIO_URL,
                                         headers={'Accept': 'application/json',
                                                  'User-Agent': 'InstallMonitor/0.2.6'})
        with urllib.request.urlopen(request, timeout=12) as response:
            # Avoid fetching oversized/unbounded remote responses.
            raw = response.read(12_000_001)
        if len(raw) > 12_000_000:
            raise ValueError('Katalog überschreitet die Größenbegrenzung')
        data = json.loads(raw.decode('utf-8'))
        repos = data['data']['repositories']['linuxserver']
        if not isinstance(repos, list) or not repos:
            raise ValueError('Kein LinuxServer.io-Image-Katalog erhalten')
        images = {}
        for entry in repos:
            if not isinstance(entry, dict) or entry.get('deprecated') is True:
                continue
            name = entry.get('name')
            if isinstance(name, str) and _LSIO_NAME.fullmatch(name):
                images[name] = entry
        if not images:
            raise ValueError('Keine gültigen LinuxServer.io-Images erhalten')
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError,
            UnicodeDecodeError, OSError) as exc:
        # Do not falsely assert that a publisher image has disappeared when
        # its API is offline; a previous valid snapshot may still be used.
        with _LSIO_LOCK:
            if _LSIO_CACHE['images']:
                return _LSIO_CACHE['images']
        raise HTTPException(503, 'LinuxServer.io-Katalog derzeit nicht erreichbar: '
                            + str(exc)[:180]) from exc
    with _LSIO_LOCK:
        _LSIO_CACHE.update({'expires': time.monotonic() + 1200, 'images': images})
    return images


def _lsio_compose(name: str) -> tuple[str, str, str, str, list[str], str]:
    if not _LSIO_NAME.fullmatch(name):
        raise HTTPException(400, 'Ungültiger LinuxServer.io-Image-Name.')
    item = _lsio_images().get(name)
    if not item:
        raise HTTPException(404, 'Das Image ist nicht im aktuellen LinuxServer.io-Katalog enthalten.')
    config = item.get('config') if isinstance(item.get('config'), dict) else {}
    appname = slug(name.replace('_', '-'))
    service: dict[str, Any] = {
        'image': f'lscr.io/linuxserver/{name}:latest',
        'restart': 'unless-stopped',
    }
    notes = ['Datenquelle: offizieller LinuxServer.io-Katalog. Das Image ist nicht heruntergeladen oder gestartet worden.']
    ports = []
    for port in config.get('ports', []) if isinstance(config.get('ports'), list) else []:
        if not isinstance(port, dict) or port.get('optional') is True:
            continue
        internal = str(port.get('internal', '')).strip()
        external = str(port.get('external', '')).strip()
        # API fields are strings; retain documented TCP/UDP protocol.
        match = re.fullmatch(r'(\d{1,5})(?:/(tcp|udp))?', internal, flags=re.I)
        host = re.fullmatch(r'(\d{1,5})(?:/(tcp|udp))?', external, flags=re.I)
        if not match or not host:
            notes.append(f'Nicht eindeutig zugeordneter Port: {external} → {internal}. Dokumentation prüfen.')
            continue
        target, host_port = int(match.group(1)), int(host.group(1))
        if not (1 <= host_port <= 65535 and 1 <= target <= 65535):
            continue
        proto = (match.group(2) or host.group(2) or 'tcp').lower()
        entry = f'{host_port}:{target}' + ('/udp' if proto == 'udp' else '')
        if entry not in ports:
            ports.append(entry)
    if ports:
        service['ports'] = ports
    mounts = []
    for vol in config.get('volumes', []) if isinstance(config.get('volumes'), list) else []:
        if not isinstance(vol, dict) or vol.get('optional') is True:
            continue
        path = str(vol.get('path') or '').strip()
        if not path.startswith('/') or '..' in path.split('/') or ':' in path or '\x00' in path or len(path) > 160:
            continue
        fragment = re.sub(r'[^a-z0-9-]+', '-', path.lower().strip('/')).strip('-') or 'data'
        host_path = f'/DATA/AppData/{appname}/{fragment}'
        mount = f'{host_path}:{path}'
        if mount not in mounts:
            mounts.append(mount)
        if any(s in fragment for s in ('media', 'movies', 'downloads', 'music', 'tv', 'photos', 'video', 'library')):
            notes.append(f'{path}: Vorgeschlagenen NAS-Pfad {host_path} vor Installation durch den tatsächlichen Medien- oder Downloadpfad ersetzen.')
    if mounts:
        service['volumes'] = mounts
    notes.append('Ports und Pflicht-Volumes stammen aus dem Anbieter-Katalog; zusätzliche Umgebungsvariablen und Einrichtungsanforderungen bitte in der Dokumentation prüfen.')
    if not ports and not mounts:
        notes.append('Der Anbieter-Katalog nennt keine Pflicht-Ports oder Pflicht-Volumes; diese Konfiguration muss manuell ergänzt werden.')
        doc = {'name': appname, 'services': {appname: service},
               'x-install-monitor-review-required': True}
    else:
        doc = {'name': appname, 'services': {appname: service}}
    changes = _auto_reassign_conflicting_ports(doc) if ports else []
    notes.extend(changes)
    docs_url = f'https://docs.linuxserver.io/images/docker-{name}/'
    project = item.get('github_url', '')
    project = project if isinstance(project, str) and project.startswith('https://github.com/linuxserver/') else ''
    icon = item.get('project_logo', '')
    icon = icon if isinstance(icon, str) and icon.startswith('https://') and len(icon) < 800 else ''
    return (yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), docs_url,
            project, icon, notes, str(item.get('category') or 'Others'))


@app.get('/api/linuxserver/images')
def linuxserver_images(req: Request):
    require_auth(req)
    entries = []
    for name, img in sorted(_lsio_images().items()):
        cfg = img.get('config') if isinstance(img.get('config'), dict) else {}
        tags = img.get('tags') if isinstance(img.get('tags'), list) else []
        arches = img.get('architectures') if isinstance(img.get('architectures'), list) else []
        entries.append({
            'name': name,
            'description': str(img.get('description') or '')[:400],
            'category': str(img.get('category') or 'Sonstige')[:90],
            'version': str(img.get('version') or '')[:80],
            'tags': [x['tag'][:65] for x in tags if isinstance(x, dict) and isinstance(x.get('tag'), str)][:15],
            'architectures': [str(x.get('arch'))[:40] for x in arches if isinstance(x, dict) and x.get('arch')][:10],
            'port_count': len(cfg.get('ports') or []) if isinstance(cfg.get('ports'), list) else 0,
            'volume_count': len(cfg.get('volumes') or []) if isinstance(cfg.get('volumes'), list) else 0,
            'docs_url': f'https://docs.linuxserver.io/images/docker-{name}/',
            'project_logo': (str(img.get('project_logo'))[:800] if isinstance(img.get('project_logo'), str) and str(img.get('project_logo')).startswith('https://') else ''),
        })
    return {'images': entries, 'source': 'https://api.linuxserver.io/api/v1/images',
            'cache_minutes': 20}

def _im_default_lan_web_port(doc: dict, app_name: str) -> list[str]:
    """Expose only a confidently identified *main Web UI* in auto-discovered recipes.

    This is a source-import default, not a last-second install rewrite: the
    user may subsequently set the published port back to loopback in the
    advanced network settings and build_plan/install will preserve that choice.
    Do not touch DB/worker ports, host-network services or other explicit IPs.
    """
    services = doc.get('services')
    if not isinstance(services, dict) or not services:
        return []
    casa = doc.get('x-casaos')
    casa = casa if isinstance(casa, dict) else {}
    main = casa.get('main')
    if not isinstance(main, str) or main not in services:
        name = str(app_name).lower().replace('_', '-')
        # Prefer a service named after the project, not the first port-bearing
        # container in a multi-service Compose (often database/admin/SMTP).
        matching = [s for s in services if s.lower().replace('_', '-') == name]
        if len(matching) == 1:
            main = matching[0]
        else:
            infrastructure = ('postgres','mariadb','mysql','redis','valkey','mongo','rabbitmq',
                              'watchtower','smtp','traefik','nginx','caddy','database','worker',
                              'cloudflared','tailscale','apprise','meilisearch')
            possible = [s for s, config in services.items()
                        if isinstance(config, dict) and config.get('ports')
                        and not any(tag in s.lower() for tag in infrastructure)
                        and not any(tag in str(config.get('image','')).lower() for tag in infrastructure)]
            if len(possible) != 1:
                return []  # Ambiguous stack: preserve all restrictions.
            main = possible[0]
    service = services[main]
    if not isinstance(service, dict) or service.get('network_mode') == 'host':
        return []  # Host networking has no Docker port binding to rewrite.
    ports = service.get('ports')
    if not isinstance(ports, list):
        return []
    binding_candidates = []
    casa_port = str(casa.get('port_map') or '').strip()
    for i, entry in enumerate(ports):
        original_host = ''
        host_port = ''
        if isinstance(entry, dict):
            if str(entry.get('protocol','tcp')).lower() != 'tcp':
                continue
            original_host = str(entry.get('host_ip') or '')
            host_port = str(entry.get('published') or '')
        elif isinstance(entry, str):
            if entry.endswith(('/udp','/sctp')):
                continue
            value = entry[:-4] if entry.endswith('/tcp') else entry
            segments = value.rsplit(':', 2)
            if len(segments) == 3 and segments[0] in ('127.0.0.1','0.0.0.0'):
                original_host, host_port = segments[0], segments[1]
            elif len(segments) == 2 and segments[0].isdigit():
                host_port = segments[0]
            # Do not change range mappings or unknown formats.
        if original_host == '127.0.0.1' and host_port.isdecimal():
            binding_candidates.append((i, int(host_port)))
    if not binding_candidates:
        return []
    # Multiple Web UI candidates require the provider's explicit port_map.
    if casa_port.isdecimal():
        choices = [(i,port) for i,port in binding_candidates if port == int(casa_port)]
    else:
        choices = binding_candidates if len(binding_candidates) == 1 else []
    if len(choices) != 1:
        return []
    index, host_port = choices[0]
    entry = ports[index]
    if isinstance(entry, dict):
        entry['host_ip'] = '0.0.0.0'
    else:
        assert isinstance(entry, str)
        ports[index] = '0.0.0.0' + entry[len('127.0.0.1'):]
    return [f'{main}: Web-Port {host_port} für NAS-IP freigegeben (0.0.0.0 statt 127.0.0.1). ' 
            'Nur die Haupt-Weboberfläche geändert; andere Dienste bleiben unverändert. '
            'In den erweiterten Netzwerkeinstellungen kann \"Nur NAS\" ausgewählt werden. '
            '0.0.0.0 bindet alle IPv4-Schnittstellen; NAS-Firewall beachten.']


@app.post("/api/analyze")
def analyze(req: Request, payload: Source):
    require_write(req)
    return _analyze_source_payload(payload)


def _analyze_source_payload(payload: Source):
    # Docker Hub web links are identifiers for Docker images, NOT Compose URLs.
    # Reuse the image pipeline, including publisher documentation and OCI
    # metadata, instead of downloading and parsing arbitrary Hub HTML.
    hub = _dockerhub_image_from_url(payload.value) if payload.kind == 'url' else None
    if hub is not None:
        image, publisher_url = hub
        _public_remote(payload.value.strip())
        normalized = payload.model_copy(update={'kind': 'image', 'value': image})
        result = _analyze_source_payload(normalized)
        document = safe_yaml(result['source'])
        safety_notes = _dockerhub_url_safe_draft(document, image)
        document[_DOC_IMAGE_PREFLIGHT] = True  # Verify published tag before ZimaOS POST.
        result['source'] = yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
        result['project_url'] = publisher_url
        result['notes'] = [
            'Docker-Hub-Projektlink erkannt: ' + publisher_url +
            ' → ' + image + '. Für den gewählten Image-Tag wird vor der Installation '
            'ein Registry-Manifest geprüft.',
            'Docker Hub dokumentiert das Image; diese Quellanalyse garantiert keine '
            'vollständige Installationskonfiguration. Datenpfade und Dienste prüfen.',
        ] + safety_notes + result['notes']
        result['automation']['source_type'] = 'url'
        result['automation']['verified_publisher_compose'] = bool(
            result['resolved_url'] and not document.get('x-install-monitor-review-required'))
        return result
    project_url = icon_url = resolved_url = ''
    source_notes: list[str] = []
    var_notes: list[str] = []
    if payload.kind == "lsio":
        content, resolved_url, project_url, icon_url, source_notes, _ = _lsio_compose(payload.value.strip())
    elif payload.kind == "image":
        image = payload.value.strip()
        if not IMAGE.fullmatch(image):
            raise HTTPException(400, "Ungültiger Docker-Image-Name.")
        appname = slug(image.split("/")[-1].split(":")[0].replace("_", "-"))
        # Explicitly chosen overrides are authoritative; never replace a
        # user's hand-configured ports or mounts with a publisher template.
        discovered = None
        if not (payload.container_port or payload.host_port or payload.config_path):
            discovered = _dockerhub_publisher_documentation(image)
            if discovered is None:
                try:
                    discovered = _publisher_compose_for_image(image)
                except HTTPException as exc:
                    # Public GitHub rate limits and unavailable publisher repos
                    # are not proof that an image is un-installable. Continue
                    # with local/OCI metadata, while retaining this warning.
                    if exc.status_code not in (400, 404, 429, 503):
                        raise
                    source_notes.append('Herausgeber-Compose derzeit nicht abrufbar: '
                                        + str(exc.detail)[:180] + '. Versuche OCI-Analyse.')
        if discovered is None and image.lower() in (
                'clamav/clamav', 'clamav/clamav:latest',
                'docker.io/clamav/clamav', 'docker.io/clamav/clamav:latest'):
            # Official ClamAV Docker documentation specifies /var/lib/clamav
            # for database persistence. ClamAV has no Web UI, and its clamd
            # TCP listener must never be published by an automatic draft.
            # Keep host storage under the ZimaOS-managed AppData directory.
            # No scan-folder mount is invented: users select their own later.
            image = 'clamav/clamav:latest'
            clamav_doc = {
                'name': 'clamav',
                'services': {'clamav': {
                    'image': image, 'restart': 'unless-stopped',
                    'volumes': ['/DATA/AppData/clamav/database:/var/lib/clamav'],
                }},
                _DOC_IMAGE_PREFLIGHT: True,
            }
            discovered = (
                yaml.safe_dump(clamav_doc, allow_unicode=True, sort_keys=False),
                'https://docs.clamav.net/manual/Installing/Docker.html',
                'https://hub.docker.com/r/clamav/clamav',
                [
                    'ClamAV: sicherer Einzelcontainer nach offizieller Docker-Dokumentation. '
                    'Die Signaturdatenbank liegt dauerhaft in /DATA/AppData/clamav/database.',
                    'ClamAV stellt keine Weboberfläche bereit. Ports 3310 und 7357 werden '
                    'nicht automatisch am NAS veröffentlicht (ungeschützte TCP-Dienste).',
                    'Es ist noch kein NAS-Ordner zum Virenscannen eingebunden. '
                    'Diesen bei Bedarf als schreibgeschützten Bind-Mount selbst auswählen; '
                    'Installation des Scan-Dienstes startet keine automatische Dateiprüfung.',
                    'Erster Datenbankdownload kann dauern; die Datenbank im gemounteten '
                    'Verzeichnis kann durch ClamAV mit angepassten Besitzrechten verwaltet werden.',
                ],
            )
        if discovered is not None:
            content, resolved_url, project_url, source_notes = discovered
            content, var_notes = _resolve_compose_variables(content)
        else:
            metadata = inspect_local_image_metadata(image)
            remote_notice = ''
            if metadata is None and not (payload.container_port or payload.host_port or payload.config_path):
                metadata, remote_notice = inspect_remote_image_metadata(image)
                if metadata:
                    source_notes.append('Image-Konfiguration anonym aus der OCI-Registry gelesen; kein Download oder Containerstart.')
            if remote_notice:
                source_notes.append(remote_notice)
            if metadata and not (payload.container_port or payload.host_port or payload.config_path):
                document, metadata_notes = _metadata_compose_draft(image, appname, metadata)
                document['x-install-monitor-review-required'] = True
                content = yaml.safe_dump(document, sort_keys=False)
                source_notes.extend(metadata_notes)
            else:
                service: dict[str, Any] = {"image": image, "restart": "unless-stopped"}
                if payload.container_port:
                    hp = payload.host_port or payload.container_port
                    if hp in RESERVED:
                        raise HTTPException(400, f"Host-Port {hp} ist reserviert.")
                    service["ports"] = [f"{hp}:{payload.container_port}"]
                if payload.config_path:
                    if not payload.config_path.startswith("/") or ".." in payload.config_path.split("/"):
                        raise HTTPException(400, "Container-Speicherpfad muss ein absoluter Pfad sein.")
                    service["volumes"] = [f"/DATA/AppData/{appname}:{payload.config_path}"]
                draft_doc = {"name": appname, "services": {appname: service}}
                if not payload.container_port and not payload.config_path:
                    draft_doc['x-install-monitor-review-required'] = True
                content = yaml.safe_dump(draft_doc, sort_keys=False)
                if not payload.container_port and not payload.config_path:
                    source_notes.append(
                        'Das Image ist nicht lokal vorhanden oder Docker-Inspect ist nicht erreichbar. '
                        'Ohne Image-Download sind Ports, Volumes und Umgebungsvariablen nicht auslesbar. '
                        'Dies ist nur ein unvollständiger Einzelcontainer-Entwurf; offizielle Anleitung prüfen.')
                else:
                    source_notes.append(
                        'Manuelle Docker-Image-Konfiguration gewählt. Install Monitor ändert die angegebenen '
                        'Ports und Datenpfade nicht. Weitere Abhängigkeiten gegebenenfalls prüfen.')
    elif payload.kind == "url":
        content, resolved_url, source_notes = discover_source(payload.value)
        original_compose = content
        if urllib.parse.urlsplit(payload.value).hostname == 'github.com':
            content, image_notes = _im_prefer_documented_publisher_image(content, resolved_url)
            source_notes.extend(image_notes)
            content, env_notes = _inline_github_env_templates(content, resolved_url)
            source_notes.extend(env_notes)
        content, var_notes = _resolve_compose_variables(content)
    elif payload.kind == "yaml":
        content, var_notes = _resolve_compose_variables(payload.value)
    else:
        raise HTTPException(400, "Unbekannte Quelle.")
    doc = safe_yaml(content)
    image_suggestions: list[dict] = []
    if payload.kind == "url" or (payload.kind == "image" and project_url):
        project_url, icon_url, icon_notes = _project_info(
            project_url if payload.kind == "image" else payload.value, resolved_url, doc)
        source_notes.extend(icon_notes)
        if payload.kind == 'url' and any('build' in svc for svc in doc['services'].values()):
            if project_url.startswith('https://codeberg.org/'):
                doc, build_notes = _attach_codeberg_build_context(doc, project_url, resolved_url,
                                                                 original_compose)
            else:
                doc, build_notes = _attach_github_build_context(doc, project_url, resolved_url)
            source_notes.extend(build_notes)
            content = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)
        image_notes = (_published_images_in_readme(project_url, resolved_url, doc, image_suggestions)
                       if payload.kind == 'url' else [])
        if image_notes:
            content = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)
            source_notes.extend(image_notes)
    elif payload.kind != 'lsio':
        upstream_icon = (doc.get("x-casaos") or {}).get("icon", "") if isinstance(doc.get("x-casaos"), dict) else ""
        icon_url = upstream_icon if isinstance(upstream_icon, str) and upstream_icon.startswith("https://") else ""
    if isinstance(doc.get('name'), str) and doc['name'].strip():
        name = doc['name']
    elif payload.kind == 'url' and project_url.startswith(('https://github.com/', 'https://codeberg.org/', 'https://gitea.baerentsen.space/')):
        # A multi-service app often declares infrastructure (postgres, redis)
        # first. Use its repository identity instead of naming the whole app
        # after the database container.
        name = project_url.rstrip('/').split('/')[-1]
    else:
        infrastructure = ('postgres', 'redis', 'mysql', 'mariadb', 'mongo', 'valkey', 'rabbitmq')
        name = next((key for key, svc in doc['services'].items()
                     if not any(tag in str(svc.get('image', '')).lower() for tag in infrastructure)),
                    next(iter(doc['services'])))
    name = slug(str(name))
    # Migrate DSM Docker bind mounts at import time, before the user edits
    # credentials and paths. The same policy runs at plan build for direct YAML.
    if payload.kind in ('yaml', 'url'):
        dsm_notes = _im_convert_synology_binds(doc, name, f'/DATA/AppData/{name}')
        if dsm_notes:
            source_notes.extend(dsm_notes)
            content = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)
        source_notes.extend(_im_wordpress_network_references(doc))
        if dsm_notes:
            source_notes.extend(_im_wordpress_dependency_cleanup(doc))
        if dsm_notes or _get_service_environment(doc['services'].get('phpmyadmin', {}), 'PMA_HOST') == 'db':
            content = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)
    if not project_url and payload.kind in ('yaml', 'image'):
        project_url = _embedded_compose_github(doc)
    icon_search_terms = _compose_icon_terms(doc, name, payload.value if payload.kind == 'image' else '')
    # Generic port optimization: only confirmed free alternatives and only on
    # automatically discovered definitions, never user-entered YAML or overrides.
    if payload.kind == 'image' and not (payload.container_port or payload.host_port or payload.config_path):
        if any(svc.get('ports') for svc in doc['services'].values()):
            changes = _auto_reassign_conflicting_ports(doc)
            if changes:
                content = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
                source_notes.extend(changes)
    # Automatic publisher/catalog imports default the main app Web UI to LAN.
    # Pasted YAML is treated as an explicit user configuration and preserved.
    # This is done at import time so the user's later 'Nur NAS' selection sticks.
    if payload.kind in ('url', 'image', 'lsio'):
        lan_notes = _im_default_lan_web_port(doc, name)
        if lan_notes:
            content = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
            source_notes.extend(lan_notes)
    notes = _warnings(doc)
    if payload.kind in ("url", "image", "lsio"):
        notes = source_notes + var_notes + notes
    elif payload.kind == "yaml":
        notes = source_notes + var_notes + notes
    return {"source": content, "name": name, "title": name.replace("-", " ").title(),
            "services": list(doc["services"]), "optional_profiles": optional_profiles(doc), "notes": notes,
            "resolved_url": resolved_url if payload.kind in ("url", "image", "lsio") else "",
            "project_url": project_url, "icon_url": icon_url, "icon_search_terms": icon_search_terms, "image_suggestions": image_suggestions,
            "automation": {"source_type": payload.kind,
                           "verified_publisher_compose": bool(resolved_url and payload.kind == 'image' and not doc.get('x-install-monitor-review-required')),
                           "official_catalog": payload.kind == 'lsio',
                           "metadata_only": bool(doc.get('x-install-monitor-review-required')),
                           "service_count": len(doc['services']),
                           "need_review": bool(doc.get('x-install-monitor-review-required'))}}



def _im_scan_worker(job_id: str, payload: Source) -> None:
    _IM_SCAN_THREAD.job_id = job_id
    try:
        _im_scan_progress('Quellprojekt wird analysiert …')
        result = _analyze_source_payload(payload)
        with _IM_SCAN_JOB_LOCK:
            if job_id in _IM_SCAN_JOBS:
                _IM_SCAN_JOBS[job_id].update({'status':'done', 'result':result, 'progress':'Analyse beendet', 'finished':time.monotonic()})
    except HTTPException as exc:
        with _IM_SCAN_JOB_LOCK:
            if job_id in _IM_SCAN_JOBS:
                _IM_SCAN_JOBS[job_id].update({'status':'error', 'error':exc.detail, 'http_status':exc.status_code, 'finished':time.monotonic()})
    except Exception as exc:
        # Log the exception class only. Messages can contain secret URLs or
        # embedded Compose values; never write those to the container logs.
        import logging
        logging.getLogger('install-monitor.scan').error('Analyseauftrag %s fehlgeschlagen: %s', job_id[:8], type(exc).__name__)
        with _IM_SCAN_JOB_LOCK:
            if job_id in _IM_SCAN_JOBS:
                _IM_SCAN_JOBS[job_id].update({'status':'error', 'error':'Quellenanalyse intern fehlgeschlagen (Fehlertyp: ' + type(exc).__name__ + '). Bitte Container-Logs prüfen.', 'http_status':500, 'finished':time.monotonic()})
    finally:
        _IM_SCAN_THREAD.job_id = None


@app.post('/api/analyze/launch')
def analyze_launch(req: Request, payload: Source):
    require_write(req)
    p = urllib.parse.urlsplit(payload.value.strip())
    if payload.kind != 'url' or p.scheme != 'https' or p.hostname != 'github.com':
        raise HTTPException(400, 'Hintergrundscan nur für GitHub-Repositories. Andere Quellen weiterhin direkt prüfen.')
    _public_remote(payload.value.strip())
    with _IM_SCAN_JOB_LOCK:
        now = time.monotonic()
        for key, value in list(_IM_SCAN_JOBS.items()):
            if value.get('finished',0) and now - value['finished'] > 1800:
                del _IM_SCAN_JOBS[key]
        if len([x for x in _IM_SCAN_JOBS.values() if x['status'] in ('queued','running')]) >= 2:
            raise HTTPException(429, 'Es laufen bereits zwei GitHub-Repository-Scans. Bitte Abschluss abwarten.')
        job_id = secrets.token_hex(20)
        _IM_SCAN_JOBS[job_id]={'status':'queued','progress':'Scan eingereiht','started':now,'result':None,'error':None}
    try:
        _IM_SCAN_POOL.submit(_im_scan_worker, job_id, payload)
    except RuntimeError as exc:
        with _IM_SCAN_JOB_LOCK:
            _IM_SCAN_JOBS.pop(job_id, None)
        raise HTTPException(503, 'Hintergrundanalyse momentan nicht verfügbar. Direkte Analyse verwenden.') from exc
    return {'job_id':job_id, 'status':'queued'}


@app.get('/api/analyze/job/{job_id}')
def analyze_job(req: Request, job_id: str):
    require_auth(req)
    if not re.fullmatch(r'[a-f0-9]{40}',job_id):
        raise HTTPException(404,'Analyse nicht gefunden.')
    with _IM_SCAN_JOB_LOCK:
        job = _IM_SCAN_JOBS.get(job_id)
        if job is None:
            raise HTTPException(404,'Analyse nicht mehr verfügbar.')
        return {'status':job['status'], 'progress':job['progress'],
                'result':job.get('result') if job['status']=='done' else None,
                'error':job.get('error') if job['status']=='error' else None,
                'http_status':job.get('http_status',400)}

@app.post("/api/source/image")
def replace_source_image(req: Request, payload: SourceImageReplacement):
    """Explicit replacement, only upon clicking the publisher-image button.

    Do not modify the original source merely because the README names another
    image. Removing the build instruction is also an explicit consequence of
    choosing a published prebuilt image.
    """
    require_write(req)
    if not IMAGE.fullmatch(payload.expected_image) or not IMAGE.fullmatch(payload.replacement_image):
        raise HTTPException(400, 'Ungültiger Docker-Image-Name.')
    if payload.expected_image == payload.replacement_image:
        raise HTTPException(400, 'Das neue Image ist identisch.')
    doc = safe_yaml(payload.source)
    svc = doc['services'].get(payload.service)
    if svc is None or str(svc.get('image')) != payload.expected_image:
        raise HTTPException(409, 'Der Compose-Entwurf wurde seit der Analyse geändert. Bitte Quelle neu analysieren.')
    svc['image'] = payload.replacement_image
    if 'build' in svc:
        svc.pop('build')
    return {'source': yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False),
            'service': payload.service, 'image': payload.replacement_image}


@app.post("/api/ports")
def ports(req: Request, payload: PortScan):
    require_write(req)
    doc = safe_yaml(payload.source)
    active_profiles, deferred = defer_missing_local_builds(doc, payload.selected_profiles)
    select_profiles(doc, active_profiles)
    report = port_report(doc)
    report['deferred_profiles'] = deferred
    return report


@app.post("/api/ports/replace")
def ports_replace(req: Request, payload: ChangePort):
    require_write(req)
    doc = safe_yaml(payload.source)
    edited = replace_port(doc, payload.service, payload.index, payload.new_port)
    filtered = safe_yaml(edited)
    active_profiles, deferred = defer_missing_local_builds(filtered, payload.selected_profiles)
    select_profiles(filtered, active_profiles)
    report = port_report(filtered)
    report['deferred_profiles'] = deferred
    return {"source": edited, "report": report}


@app.post("/api/preview")
def preview(req: Request, payload: Plan):
    require_write(req)
    return build_plan(payload)

# Only app-owned directories under the ZimaOS AppData root are created.
# The docker daemon runs on the NAS host; the Install Monitor process runs
# inside its own container and cannot use a local os.makedirs() on host paths.
HOST_APPDATA_ROOT = "/DATA/AppData"
_FILE_MOUNT_SUFFIXES = (".env", ".json", ".yml", ".yaml", ".toml", ".ini", ".conf", ".pem", ".crt", ".key", ".db", ".sqlite", ".sqlite3", ".sock")


def _compose_host_bind_sources(doc: dict) -> list[tuple[str, bool]]:
    """Return bind-host paths and whether the source is known to be a directory.

    Keep upstream named Docker volumes without driver_opts untouched; their
    content is managed by Docker, not this preparer.
    """
    result: list[tuple[str, bool]] = []
    volumes = doc.get('volumes') or {}
    if not isinstance(volumes, dict):
        raise HTTPException(400, 'Ungültige Docker-Volumes-Konfiguration.')
    for volume in volumes.values():
        if not isinstance(volume, dict):
            continue
        opts = volume.get('driver_opts') or {}
        if not isinstance(opts, dict):
            continue
        flags = str(opts.get('o', '')).split(',')
        device = opts.get('device')
        if isinstance(device, str) and 'bind' in flags and opts.get('type') == 'none':
            result.append((device, True))
    for svc in doc['services'].values():
        for item in (svc.get('volumes') or []):
            if isinstance(item, str):
                # Form: /host/path:/container/path[:mode]. Named volumes and
                # anonymous targets do not need NAS directory preparation.
                source = item.split(':', 1)[0]
                if source.startswith('/'):
                    result.append((source, False))
            elif isinstance(item, dict) and item.get('type') == 'bind':
                source = item.get('source')
                if isinstance(source, str):
                    result.append((source, False))
    return result


def _managed_host_directories(doc: dict, app_name: str) -> list[str]:
    """Require strict, app-scoped NAS paths; never alter system/shared mounts.

    File binds and mounts outside /DATA/AppData/<app_name> are left untouched.
    The helper refuses to follow symlinks; a failing helper aborts installation.
    """
    base = f'{HOST_APPDATA_ROOT}/{app_name}'
    directories: set[str] = set()
    for raw, known_dir in _compose_host_bind_sources(doc):
        if not isinstance(raw, str) or not raw.startswith('/') or '\x00' in raw:
            raise HTTPException(400, 'Ungültiger Host-Speicherpfad in Docker Compose.')
        segments = raw.split('/')
        if '..' in segments or '.' in segments:
            raise HTTPException(400, f'Host-Speicherpfad muss ohne . oder .. angegeben werden: {raw[:160]}')
        normalized = os.path.normpath(raw)
        if normalized != base and not normalized.startswith(base + '/'):
            # Other user-supplied mounts are not rewritten or created.
            continue
        if not known_dir and normalized.lower().endswith(_FILE_MOUNT_SUFFIXES):
            # Do not create directories in place of credential/config files.
            continue
        directories.add(normalized)
    for filename in _im_wordpress_ini_templates(doc, app_name):
        directories.add(os.path.dirname(filename))
    if len(directories) > 100:
        raise HTTPException(400, 'Zu viele App-Datenverzeichnisse im Compose.')
    return sorted(directories, key=lambda x: (x.count('/'), x))


# This script runs only in a disposable, network-isolated helper container.
# Docker bind-mounts the NAS /DATA/AppData directory writable at /im-appdata;
# the service's own root filesystem remains read-only.  No host shell command
# and no ZimaOS credentials are passed to the helper.
_HOST_DIRECTORY_PREPARER = r'''
import json, os, stat
from pathlib import Path
root = Path('/im-appdata')
app = os.environ['IM_PREPARE_APP']
paths = json.loads(os.environ['IM_PREPARE_PATHS'])
owners = json.loads(os.environ.get('IM_PREPARE_OWNERS', '{}'))
templates = json.loads(os.environ.get('IM_PREPARE_TEMPLATES', '{}'))
if not app or any(ch not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in app):
    raise RuntimeError('invalid application name')
created = []
for absolute in paths:
    prefix = '/DATA/AppData/' + app
    if absolute != prefix and not absolute.startswith(prefix + '/'):
        raise RuntimeError('path outside app namespace')
    relative = absolute[len('/DATA/AppData/'):]
    parts = relative.split('/')
    if any(not p or p in ('.', '..') for p in parts):
        raise RuntimeError('invalid directory segment')
    current = root
    for segment in parts:
        current = current / segment
        try:
            entry = current.lstat()
        except FileNotFoundError:
            current.mkdir(mode=0o755)
            created.append(str(current).replace('/im-appdata/', '/DATA/AppData/', 1))
            entry = current.lstat()
        if not stat.S_ISDIR(entry.st_mode) or stat.S_ISLNK(entry.st_mode):
            raise RuntimeError('not a real directory: ' + str(current))
for absolute in paths:
    current = root / absolute[len('/DATA/AppData/'):]
    if not current.is_dir():
        raise RuntimeError('directory not available after preparation: ' + absolute)
# The path owner is calculated from Docker image Config.User, NOT guessed
# as 1000:1000. Only directories created by THIS helper may be chowned.
owned = []
for absolute in created:
    identity = owners.get(absolute)
    if identity is None:
        continue
    uid, gid = identity
    if not all(isinstance(i, int) and 0 <= i <= 2147483647 for i in (uid, gid)):
        raise RuntimeError('invalid image identity')
    path = root / absolute[len('/DATA/AppData/'):]
    current = root
    for segment in absolute[len('/DATA/AppData/'):].split('/'):
        current = current / segment
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise RuntimeError('unsafe directory during ownership preparation')
    os.chown(path, uid, gid, follow_symlinks=False)
    owned.append(absolute)
# Create only allowlisted, static PHP ini files under the app namespace.
# Exclusive creation means pre-existing files are never changed.
created_files = []
for absolute, content in templates.items():
    if (not absolute.startswith('/DATA/AppData/' + app + '/')
        or not absolute.endswith('/uploads.ini')
        or not isinstance(content, str)
        or content != 'file_uploads=On\nmemory_limit=256M\nupload_max_filesize=64M\npost_max_size=64M\nmax_execution_time=300\n'):
        raise RuntimeError('invalid config template')
    dest = root / absolute[len('/DATA/AppData/'):]
    parent = dest.parent
    if not parent.is_dir() or parent.is_symlink():
        raise RuntimeError('config parent is unavailable')
    try:
        info = dest.lstat()
    except FileNotFoundError:
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, 'O_NOFOLLOW'): flags |= os.O_NOFOLLOW
            fd = os.open(dest, flags, 0o644)
        except FileExistsError:
            info = dest.lstat()
        else:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                out.write(content)
            created_files.append(absolute)
            info = dest.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise RuntimeError('config destination must be a regular file')
print(json.dumps({'prepared': paths, 'created': created, 'owned': owned, 'created_files': created_files}))
'''


def _im_image_uid_gid(service: dict) -> tuple[int, int] | None:
    """Best-effort image-standard identity, no user override, no host commands.

    Never pull an image or change a user setting. Named runtime users are
    resolved by an isolated id-only container if available locally.
    """
    image = str(service.get('image') or '')
    user_override = str(service.get('user') or '').strip()
    # A numeric Compose user is authoritative even before its image has been
    # pulled. In DSM migrations (redis: user 1026:100) newly created writable
    # bind directories must use this identity, otherwise Redis cannot write.
    if re.fullmatch(r'\d+:\d+', user_override):
        uid_text, gid_text = user_override.split(':', 1)
        return int(uid_text), int(gid_text)
    try:
        proc = subprocess.run(['docker', 'image', 'inspect', image,
                               '--format', '{{.Config.User}}'],
                              capture_output=True, text=True, timeout=6)
        if proc.returncode != 0:
            return None
        user = user_override or proc.stdout.strip()
        if not user:
            return (0, 0)
        if re.fullmatch(r'\d+(?::\d+)?', user):
            uid, _, gid = user.partition(':')
            return (int(uid), int(gid)) if gid else None  # UID-only: group unknown.
        # Docker's user-name lookup is image-specific. The image is run with
        # no network, no Linux caps and a read-only root. If id does not exist,
        # return unknown instead of guessing UID 1000.
        args = ['docker', 'run', '--rm', '--pull', 'never', '--network', 'none',
                '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--pids-limit', '32', '--memory', '64m', '--entrypoint', 'id']
        if user_override:
            args += ['--user', user_override]
        p1 = subprocess.run(args + [image, '-u'], capture_output=True, text=True, timeout=12)
        p2 = subprocess.run(args + [image, '-g'], capture_output=True, text=True, timeout=12)
        if p1.returncode == p2.returncode == 0 and p1.stdout.strip().isdigit() and p2.stdout.strip().isdigit():
            return int(p1.stdout.strip()), int(p2.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def _im_new_bind_owners(doc: dict, app_name: str) -> tuple[dict[str, list[int]], list[str]]:
    """Ownership map only for in-project writable binds, never named volumes.

    Multiple writers with distinct identities are not chmod/chowned blindly.
    """
    base = f'/DATA/AppData/{app_name}'
    writers: dict[str, set[tuple[int, int]]] = {}
    notes: list[str] = []
    unresolved: set[str] = set()
    identities: dict[tuple[str, str], tuple[int, int] | None] = {}
    for name, svc in doc['services'].items():
        if _service_setup_later(svc):
            continue
        for entry in (svc.get('volumes') or []):
            source, ro = None, False
            if isinstance(entry, str):
                fields = entry.split(':')
                if len(fields) >= 2 and fields[0].startswith('/'):
                    source = fields[0]
                    ro = len(fields) > 2 and 'ro' in fields[-1].split(',')
            elif isinstance(entry, dict) and entry.get('type') == 'bind':
                source = entry.get('source')
                ro = bool(entry.get('read_only'))
            if ro or not isinstance(source, str) or not (source == base or source.startswith(base + '/')):
                continue
            if source.lower().endswith(_FILE_MOUNT_SUFFIXES):
                continue
            identity_key = (str(svc.get('image') or ''), str(svc.get('user') or ''))
            if identity_key not in identities:
                identities[identity_key] = _im_image_uid_gid(svc)
            identity = identities[identity_key]
            if identity is None or any(n is None for n in identity):
                unresolved.add(f'{name}: Image-UID/GID noch nicht lokal ermittelbar; neue NAS-Ordner können weitere Schreibrechte benötigen.')
                continue
            writers.setdefault(source, set()).add(identity)
    owners: dict[str, list[int]] = {}
    for source, identities in writers.items():
        if len(identities) > 1:
            notes.append(source + ': Mehrere Schreibbenutzer mit verschiedenen UID/GID; keine automatische Eigentümeränderung.')
        elif len(identities) == 1:
            owners[source] = list(next(iter(identities)))
    return owners, notes + sorted(unresolved)


def prepare_app_directories(doc: dict, app_name: str) -> dict:
    """Synchronous, verified NAS directory preparation before the ZimaOS POST."""
    paths = _managed_host_directories(doc, app_name)
    if not paths:
        return {'prepared': [], 'created': [], 'owned': [], 'notes': []}
    owners, notes = _im_new_bind_owners(doc, app_name)
    try:
        image = subprocess.run(
            ['docker', 'inspect', 'install-monitor', '--format', '{{.Image}}'],
            text=True, capture_output=True, timeout=8, check=True,
        ).stdout.strip()
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
            raise RuntimeError('Install Monitor Docker-Image konnte nicht bestimmt werden.')
        command = [
            'docker', 'run', '--rm', '--network', 'none', '--read-only',
            '--cap-drop', 'ALL', '--cap-add', 'CHOWN',
            '--security-opt', 'no-new-privileges',
            '--pids-limit', '64', '--memory', '128m',
            '--mount', f'type=bind,source={HOST_APPDATA_ROOT},target=/im-appdata',
            '--env', f'IM_PREPARE_APP={app_name}',
            '--env', 'IM_PREPARE_PATHS=' + json.dumps(paths),
            '--env', 'IM_PREPARE_OWNERS=' + json.dumps(owners),
            '--env', 'IM_PREPARE_TEMPLATES=' + json.dumps(_im_wordpress_ini_templates(doc, app_name)),
            '--entrypoint', 'python', image, '-c', _HOST_DIRECTORY_PREPARER,
        ]
        result = subprocess.run(command, text=True, capture_output=True, timeout=45, check=True)
        response = json.loads(result.stdout)
        if response.get('prepared') != paths or not isinstance(response.get('created'), list):
            raise RuntimeError('Verzeichnisprüfung lieferte kein gültiges Ergebnis.')
        response['notes'] = notes
        return response
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
        # Do not send the install request if host directories were not confirmed.
        detail = (exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)) or str(exc)
        raise HTTPException(502, 'App-Datenordner auf dem NAS konnten vor der Installation nicht '
                                 'erstellt/geprüft werden. ZimaOS wurde nicht beauftragt: '
                                 + detail.strip()[-320:]) from exc


@app.post("/api/install")
def install(req: Request, payload: Install):
    require_write(req)
    if payload.target_system != "zimaos":
        raise HTTPException(400,"Das gewählte Zielsystem unterstützt derzeit nur den Compose-Export.")
    payload = _install_target(req, payload)
    if not payload.confirmed:
        raise HTTPException(400, "Installation benötigt eine ausdrückliche Bestätigung.")
    doc = safe_yaml(payload.compose)
    _validate_legacy_env_files(doc)
    _validate_gpu_access_at_install(doc)
    name = slug(str(doc.get("name", "")))
    casa = doc.get("x-casaos")
    if not isinstance(casa, dict) or not casa.get("id") or not casa.get("main"):
        raise HTTPException(400, "ZimaOS-Metadaten fehlen.")
    unresolved = _unresolved_runtime_variables(doc)
    if unresolved:
        raise HTTPException(400, 'Compose enthält offene Laufzeitvariablen: ' + ', '.join(sorted(unresolved)))
    if any('build' in svc for svc in doc['services'].values()):
        raise HTTPException(400, 'GitHub-Quellcode benötigt den Live-Installationsablauf mit Build-Bestätigung.')
    missing = _setup_issues(doc) + _im_host_file_mount_issues(doc) + _im_unconverted_synology_binds(doc) + _im_wordpress_credentials_issues(doc) + _im_wordpress_weak_password_issues(doc) + _project_image_issues(doc, name)
    missing += [f'{service}: {key} fehlt' for service, key in _required_credentials(doc)]
    if missing:
        raise HTTPException(400, 'Installationsvoraussetzungen fehlen: ' + ' · '.join(missing))
    require_ports_free(doc)
    base = safe_host(payload.host)
    token = zima_login(base, payload.username, payload.password)
    # Reject overwriting an existing app; this is an installer, not Update Monitor.
    status, _ = api_call(base, f"/v2/app_management/compose/{urllib.parse.quote(name)}", "GET", token=token)
    if status == 200:
        raise HTTPException(409, f"App '{name}' existiert bereits. Keine vorhandene Installation wird überschrieben.")
    if status not in (400, 404):
        raise HTTPException(502, f"Installationsprüfung fehlgeschlagen: ZimaOS HTTP {status}.")
    # The synchronous helper must finish and verify host directories before
    # ZimaOS receives the Compose YAML.  This prevents the CasaDrop bind-volume
    # race: a missing source directory makes Docker reject container creation.
    prepared = prepare_app_directories(doc, name)
    code, response = api_call(base, "/v2/app_management/compose", "POST", token, payload.compose, "application/yaml")
    if code not in (200, 201, 202):
        raise HTTPException(502, f"ZimaOS hat die Installation abgelehnt (HTTP {code}): {response[:280]}")
    return {"accepted": True, "name": name, "directories": prepared,
            "message": "App-Datenordner geprüft. ZimaOS hat die Installation angenommen. Containerstatus anschließend prüfen."}


# Installation jobs are private to the authenticated session and live only in
# memory.  Credentials are passed only to the worker, never stored in job status.
INSTALL_JOBS: dict[str, dict] = {}
INSTALL_JOBS_LOCK = threading.RLock()
INSTALL_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='im-install')
INSTALL_PHASES = ('preflight', 'login', 'existing', 'build', 'directories', 'submitted', 'containers', 'startup', 'verification')
VERIFY_TIMEOUT_SECONDS = 360


def _im_safe_runtime_error(error: str, doc: dict) -> str:
    """Expose the complete bounded OCI diagnosis without known Compose secrets."""
    value = str(error or '').strip()
    for service in (doc.get('services') or {}).values():
        if not isinstance(service, dict):
            continue
        for key, secret in _im_environment_entries(service).items():
            if (re.search(r'(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|MASTER_KEY)', key, re.I)
                    and len(secret) >= 8):
                value = value.replace(secret, '[REDACTED]')
    value = re.sub(r'(?i)(://[^:/\s]+:)[^@/\s]+(@)', r'\1[REDACTED]\2', value)
    return value[:1400]


def _job_update(job_id: str, *, phase: str | None = None, message: str | None = None,
                state: str | None = None, containers: list | None = None,
                events: str | None = None, accepted: bool | None = None) -> None:
    with INSTALL_JOBS_LOCK:
        job = INSTALL_JOBS.get(job_id)
        if job is None:
            return
        if phase is not None:
            job['phase'] = phase
        if message is not None:
            job['message'] = message[:1500]
        if state is not None:
            job['state'] = state
        if containers is not None:
            job['containers'] = containers[:20]
        if accepted is not None:
            job['accepted'] = accepted
        if events:
            job['events'].append({'at': time.strftime('%H:%M:%S'), 'message': events[:1500]})
            job['events'] = job['events'][-60:]
        job['updated'] = time.monotonic()


def _read_compose_containers(name: str) -> list[dict]:
    """Only project-labeled Docker containers; never inspect environment/secrets."""
    proc = subprocess.run(
        ['docker', 'ps', '-a', '--filter', f'label=com.docker.compose.project={name}',
         '--format', '{{.ID}} {{.Label "com.docker.compose.service"}}'],
        capture_output=True, text=True, timeout=10, check=True)
    result = []
    for line in proc.stdout.splitlines()[:20]:
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            continue
        ident, service = fields
        if not re.fullmatch(r'[a-f0-9]{12,64}', ident) or not re.fullmatch(r'[\w-]{1,70}', service):
            continue
        state_proc = subprocess.run(
            ['docker', 'inspect', '--format', '{{json .State}}', ident],
            capture_output=True, text=True, timeout=7, check=True)
        raw = json.loads(state_proc.stdout)
        health = (raw.get('Health') or {}).get('Status') if isinstance(raw.get('Health'), dict) else None
        result.append({'service': service, 'id': ident,
                       'state': str(raw.get('Status') or 'unknown'),
                       'health': health or '', 'exit_code': raw.get('ExitCode'),
                       'error': str(raw.get('Error') or '')[:1600]})
    return sorted(result, key=lambda x: x['service'])


def _im_readonly_mounts(ident: str) -> list[dict] | None:
    """Read Docker mount *metadata* only; never read files or secrets."""
    if not re.fullmatch(r'[0-9a-f]{12,64}', ident or ''):
        return None
    try:
        proc = subprocess.run(['docker', 'inspect', '--format', '{{json .Mounts}}', ident],
                              capture_output=True, text=True, timeout=6, check=True)
        mounts = json.loads(proc.stdout)
        return mounts if isinstance(mounts, list) else None
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def _im_expected_shared_volume_mounts(doc: dict) -> dict[str, list[tuple[str, str]]]:
    """Map a declared named volume to the service and container target."""
    declared = doc.get('volumes') or {}
    if not isinstance(declared, dict):
        return {}
    result: dict[str, list[tuple[str, str]]] = {}
    for service_name, service in (doc.get('services') or {}).items():
        if not isinstance(service, dict) or _service_setup_later(service):
            continue  # Explicitly deferred services do not belong to this rollout.
        for item in service.get('volumes') or []:
            if isinstance(item, str):
                bits = item.split(':')
                if len(bits) < 2:
                    continue
                source, target = bits[:2]
                read_only = len(bits) >= 3 and 'ro' in bits[-1].split(',')
            elif isinstance(item, dict) and item.get('type') == 'volume':
                source, target = item.get('source'), item.get('target')
                read_only = bool(item.get('read_only'))
            else:
                continue
            if source in declared and isinstance(target, str):
                result.setdefault(source, []).append((service_name, target, read_only))
    return {key: uses for key, uses in result.items() if len({s for s, _, _ in uses}) >= 2}


def _im_runtime_shared_volume_issues(doc: dict, observed: list[dict]) -> list[str]:
    """Verify *actual* bind/volume identity before claiming multi-service success.

    No mutation or ownership repair: unexpected /app/data sources are reported.
    On unavailable Docker inspection fail conservatively for shared volumes.
    """
    shared = _im_expected_shared_volume_mounts(doc)
    if not shared:
        return []
    by_name = {o.get('service'): o for o in observed}
    all_names = {service for uses in shared.values() for service, _, _ in uses}
    actual = {}
    for service in all_names:
        ident = str(by_name.get(service, {}).get('id') or '')
        mounts = _im_readonly_mounts(ident)
        if mounts is None:
            return ['Gemeinsame Docker-Volumes konnten nicht für alle Dienste überprüft werden; keine endgültige Bestätigung.']
        actual[service] = {str(m.get('Destination')): (str(m.get('Source')), m.get('RW'))
                           for m in mounts if isinstance(m, dict) and m.get('Destination') and m.get('Source')}
    problems = []
    for volume, uses in shared.items():
        paths = {actual[s].get(target, (None, None))[0] for s, target, _ in uses}
        if None in paths:
            problems.append(f'Docker-Volume {volume}: Der Mount fehlt in mindestens einem Dienst.')
        elif len(paths) > 1:
            problems.append(f'Docker-Volume {volume}: Dienste verwenden unterschiedliche Host-Datenquellen; Installation nicht konsistent.')
        for service, target, read_only in uses:
            observed_rw = actual[service].get(target, (None, None))[1]
            if observed_rw is not None and bool(observed_rw) == read_only:
                problems.append(f'{service}: Schreibschutz des Docker-Volumes {volume} entspricht nicht dem Compose-Mount.')
    return problems


def _im_container_log_hint(ident: str) -> str:
    """Classify small recent log tail locally. Never expose raw logs/credentials."""
    if not re.fullmatch(r'[0-9a-f]{12,64}', ident or ''):
        return ''
    try:
        proc = subprocess.run(['docker', 'logs', '--tail', '60', ident],
                              capture_output=True, text=True, timeout=6, check=False)
        raw = (proc.stdout + '\n' + proc.stderr)[-18000:].lower()
    except (OSError, subprocess.TimeoutExpired):
        return ''
    if 'eacces' in raw or 'permission denied' in raw or 'eperm' in raw:
        return 'EACCES/Berechtigungen: Containerbenutzer kann einen Mount möglicherweise nicht beschreiben. UID/GID, :ro und Host-Dateirechte prüfen; kein pauschales chmod 777.'
    if 'unsettled top-level await' in raw:
        return 'Node.js Exit 13: Ein asynchroner Startvorgang endet nicht. Datenbank, gemeinsame Volumes und externe Abhängigkeiten prüfen; Ursache nicht automatisch bestimmbar.'
    if 'enospc' in raw or 'no space left on device' in raw:
        return 'Speicherplatz fehlt (ENOSPC): Freien Speicher und Inodes des NAS-Datenträgers kontrollieren.'
    if 'eaddrinuse' in raw or 'address already in use' in raw or 'port is already allocated' in raw:
        return 'Port belegt: Host-Port beziehungsweise interne Dienst-Portkonflikte überprüfen.'
    if 'sqlite_cantopen' in raw or 'unable to open database file' in raw:
        return 'SQLite-Datenbankdatei nicht erreichbar: Schreibrechte und gemeinsam genutzten Daten-Mount prüfen.'
    if 'connection refused' in raw or 'econnrefused' in raw:
        return 'Verbindung abgelehnt: Adresse, Startreihenfolge und Erreichbarkeit des abhängigen Dienstes prüfen.'
    if 'getaddrinfo enotfound' in raw or 'name or service not known' in raw:
        return 'DNS/Dienstname nicht auflösbar: Compose-Netzwerke und Dienstnamen prüfen.'
    return ''


def _im_failure_summary(observed: list[dict], doc: dict) -> str:
    """Short safe diagnostic that the existing installation UI can display."""
    names = set(doc.get('services') or {})
    for item in observed:
        if item.get('service') not in names:
            continue
        if item.get('state') in ('restarting', 'exited', 'dead') or item.get('health') == 'unhealthy':
            hint = _im_container_log_hint(str(item.get('id') or ''))
            if hint:
                return str(item['service']) + ': ' + hint
    return 'Container-Logs und alle Dienstabhängigkeiten überprüfen. Keine automatische Rechteänderung durchgeführt.'


def _local_image_count(services: dict) -> tuple[int, int]:
    """Real host image presence; never invent layer percentages."""
    images = {str(svc.get('image', '')) for svc in services.values()}
    try:
        proc = subprocess.run(['docker', 'image', 'ls', '--format', '{{.Repository}}:{{.Tag}}'],
                              capture_output=True, text=True, check=True, timeout=8)
        present = set(proc.stdout.splitlines())
        return len(images.intersection(present)), len(images)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return 0, len(images)


def _check_runtime(services: dict, main_service: str, observed: list[dict]) -> tuple[bool, str, list[str]]:
    """A green result requires every non-deferred service to run, not an HTTP 200."""
    by_service = {item['service']: item for item in observed}
    deferred = {name for name, svc in services.items() if _service_setup_later(svc)}
    required = [name for name in services if name not in deferred]
    missing = [name for name in required if name not in by_service]
    stopped = [name for name in required if name in by_service and by_service[name]['state'] != 'running']
    unhealthy = [name for name in required if name in by_service and by_service[name]['health'] == 'unhealthy']
    if missing:
        return False, 'Container fehlen noch: ' + ', '.join(missing), deferred
    if stopped:
        return False, 'Container noch nicht gestartet: ' + ', '.join(stopped), deferred
    if unhealthy:
        return False, 'Container nicht gesund: ' + ', '.join(unhealthy), deferred
    pending = [name for name in required if by_service[name]['health'] == 'starting']
    if pending:
        return False, 'Healthcheck läuft: ' + ', '.join(pending), deferred
    if main_service not in by_service or by_service[main_service]['state'] != 'running':
        return False, f'Hauptdienst {main_service} läuft noch nicht.', deferred
    if deferred:
        return True, 'Hauptanwendung läuft. Einrichtung ausstehend: ' + ', '.join(sorted(deferred)), deferred
    return True, 'Alle ausgewählten Container laufen.', deferred


def _validate_install_payload(payload: Install) -> tuple[dict, str]:
    if not payload.confirmed:
        raise HTTPException(400, 'Installation benötigt eine ausdrückliche Bestätigung.')
    doc = safe_yaml(payload.compose)
    _validate_legacy_env_files(doc)
    _validate_gpu_access_at_install(doc)
    name = slug(str(doc.get('name', '')))
    casa = doc.get('x-casaos')
    if not isinstance(casa, dict) or not casa.get('id') or not casa.get('main'):
        raise HTTPException(400, 'ZimaOS-Metadaten fehlen.')
    if str(casa['main']) not in doc['services']:
        raise HTTPException(400, 'Hauptdienst in x-casaos.main nicht vorhanden.')
    contract_errors, _ = _im_zimaos_contract_checks(doc)
    if contract_errors:
        raise HTTPException(400, 'ZimaOS-Compose-Prüfung: ' + ' · '.join(contract_errors))
    unresolved = _unresolved_runtime_variables(doc)
    if unresolved:
        raise HTTPException(400, 'Compose enthält offene Laufzeitvariablen: ' + ', '.join(sorted(unresolved)))
    if any('build' in svc for svc in doc['services'].values()):
        _validated_builds(doc)
        if not payload.build_confirmed:
            raise HTTPException(400, 'Lokaler Docker-Build erfordert eine separate ausdrückliche Bestätigung.')
    issues = _setup_issues(doc) + _im_host_file_mount_issues(doc) + _im_unconverted_synology_binds(doc) + _im_wordpress_credentials_issues(doc) + _im_wordpress_weak_password_issues(doc) + _app_url_issues(doc) + _project_image_issues(doc, name)
    issues += [f'{service}: {key} fehlt' for service, key in _required_credentials(doc)]
    if issues:
        raise HTTPException(400, 'Installationsvoraussetzungen fehlen: ' + ' · '.join(issues))
    return doc, name


def _job_worker(job_id: str, payload: Install) -> None:
    """Execute exactly one ZimaOS install and verify real Docker states."""
    try:
        _job_update(job_id, phase='preflight', state='running', message='Host-Ports und Compose werden geprüft.', events='Prüfung gestartet.')
        doc, name = _validate_install_payload(payload)
        require_ports_free(doc)
        base = safe_host(payload.host)
        _job_update(job_id, phase='login', message='Verbindung zu ZimaOS wird hergestellt.', events='Host-Ports sind frei.')
        token = zima_login(base, payload.username, payload.password)
        _job_update(job_id, phase='existing', message='Vorhandene Installation wird ausgeschlossen.')
        status, _ = api_call(base, f'/v2/app_management/compose/{urllib.parse.quote(name)}', 'GET', token=token)
        if status == 200:
            raise HTTPException(409, f"App '{name}' existiert bereits. Keine vorhandene Installation wird überschrieben.")
        if status not in (400, 404):
            raise HTTPException(502, f'Installationsprüfung fehlgeschlagen: ZimaOS HTTP {status}.')
        # Crucial for README/docker.md fallbacks: reject an unavailable tag
        # before any app-data changes or ZimaOS installation POST can occur.
        _verify_documented_images(doc, job_id)
        local_mode = _uses_private_local_images(doc)
        if local_mode and _read_compose_containers(name):
            raise HTTPException(409, 'Docker-Compose-Projekt ist bereits vorhanden. Keine bestehende Installation wird überschrieben.')
        if any('build' in svc for svc in doc['services'].values()):
            _job_update(job_id, phase='build', message='Quellcode und Docker-Image werden vorbereitet.', events='Lokaler Build bestätigt.')
            _build_local_images(doc, job_id)
        _job_update(job_id, phase='directories', message='App-Datenordner werden erstellt und geprüft.', events='ZimaOS-Anmeldung erfolgreich.')
        prepared = prepare_app_directories(doc, name)
        for note in prepared.get('notes', [])[:5]:
            _job_update(job_id, events='Berechtigungsprüfung: ' + note)
        if prepared.get('owned'):
            _job_update(job_id, events=f"Nur neu erstellte NAS-Ordner: {len(prepared['owned'])} anhand der Image-UID/GID vorbereitet.")
        if local_mode:
            # The ZimaOS API must install every application to create its native
            # dashboard entry. Do not silently fall back to unmanaged compose.
            install_doc = _publish_local_images(doc, job_id)
            _job_update(job_id, phase='submitted', message='Registriere die Anwendung über ZimaOS.',
                        events=f"Datenordner bestätigt: {len(prepared['prepared'])}; neu: {len(prepared['created'])}.")
        else:
            install_doc = doc
            _job_update(job_id, phase='submitted', message='Installationsauftrag wird an ZimaOS übermittelt.',
                        events=f"Datenordner bestätigt: {len(prepared['prepared'])}; neu: {len(prepared['created'])}.")
        code, response = api_call(base, '/v2/app_management/compose', 'POST', token,
                                  _zimaos_compose(install_doc), 'application/yaml')
        if code not in (200, 201, 202):
            raise HTTPException(502, f'ZimaOS hat die Installation abgelehnt (HTTP {code}): {response[:280]}')
        _job_update(job_id, phase='containers', accepted=True,
                    message='ZimaOS hat den Auftrag angenommen. Docker-Container werden beobachtet.',
                    events=f'ZimaOS-Auftrag angenommen (HTTP {code}).')
        main_service = str(doc['x-casaos']['main'])
        previous: tuple = ()
        previous_images: tuple[int, int] | None = None
        attempted_start = False
        main_created_at: float | None = None
        observed: list[dict] = []
        stable_since: float | None = None
        failing_since: dict[str, float] = {}
        deadline = time.monotonic() + VERIFY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                observed = _read_compose_containers(name)
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as exc:
                _job_update(job_id, message=f'Docker-Status vorübergehend nicht verfügbar: {type(exc).__name__}.')
                time.sleep(2)
                continue
            snapshot = tuple((item['service'], item['state'], item['health'], item['exit_code']) for item in observed)
            if snapshot != previous:
                previous = snapshot
                if observed:
                    detail = ', '.join(f"{item['service']}: {item['state']}" + (f" ({item['health']})" if item['health'] else '') for item in observed)
                    _job_update(job_id, phase='startup', message=detail, containers=observed, events=detail)
                else:
                    _job_update(job_id, phase='containers', message='ZimaOS lädt Images und erstellt Docker-Container.', containers=[])
            if not observed:
                counts = _local_image_count(doc['services'])
                if counts != previous_images:
                    previous_images = counts
                    _job_update(job_id, phase='containers', message=f'Docker-Images vorhanden: {counts[0]}/{counts[1]}. Warten auf Containererstellung.',
                                events=f'Docker-Images auf dem NAS: {counts[0]}/{counts[1]} bereit.')
            ok, summary, deferred = _check_runtime(doc['services'], main_service, observed)
            if ok:
                if stable_since is None:
                    stable_since = time.monotonic()
                    _job_update(job_id, phase='verification', message='Laufende Container werden auf stabilen Start geprüft.', events='Laufzeitprüfung begonnen.')
                elif time.monotonic() - stable_since >= 6:
                    storage_issues = _im_runtime_shared_volume_issues(doc, observed)
                    if storage_issues:
                        _job_update(job_id, phase='verification', state='warning', containers=observed,
                                    message='Gemeinsame Docker-Datenquellen: ' + ' '.join(storage_issues)[:340],
                                    events='Gemeinsamer Storage ist nicht bestätigt. Keine Erfolgsmeldung.')
                        return
                    if local_mode:
                        # Running containers alone are insufficient: unmanaged
                        # Compose installations caused missing dashboard tiles
                        # in v0.1.31. Confirm app management owns this project.
                        registered, _ = api_call(base, f'/v2/app_management/compose/{urllib.parse.quote(name)}',
                                                 'GET', token=token)
                        if registered != 200:
                            _job_update(job_id, phase='verification', state='warning',
                                        message='Container laufen, aber ZimaOS bestätigt die App-Registrierung nicht. Dashboard-Kachel möglicherweise nicht vorhanden.',
                                        containers=observed,
                                        events=f'ZimaOS-Registrierungsprüfung: HTTP {registered}.')
                            return
                    _job_update(job_id, phase='verification', state='success', message=summary + ' ZimaOS-App-Registrierung bestätigt.' if local_mode else summary,
                                containers=observed, events='Installation bestätigt: ' + summary)
                    return
            else:
                stable_since = None
            by_service = {c['service']: c for c in observed}
            # Docker may leave a container CREATED with State.Error after a
            # failed bind mount. Surface the actual daemon error immediately;
            # six minutes of polling cannot repair an invalid host path.
            for current in observed:
                docker_error = _im_safe_runtime_error(current.get('error') or '', doc)
                if current.get('state') in ('created', 'dead', 'exited') and docker_error:
                    safe_observed = [{**item, 'error': _im_safe_runtime_error(item.get('error') or '', doc)}
                                     for item in observed]
                    detail = f"{current['service']}: Docker-Start fehlgeschlagen: " + docker_error
                    _job_update(job_id, phase='verification', state='warning', containers=safe_observed,
                                message=detail, events=detail)
                    return
            # A restart loop can be present even while ZimaOS reports the app
            # as running. Distinguish transient startup from persistent failure.
            for service_name, entry in by_service.items():
                broken = (entry.get('state') in ('restarting', 'dead')
                          or (entry.get('state') == 'exited' and entry.get('exit_code') not in (0, None)))
                if broken:
                    failing_since.setdefault(service_name, time.monotonic())
                else:
                    failing_since.pop(service_name, None)
            if any(time.monotonic() - since >= 18 for since in failing_since.values()):
                diagnosis = _im_failure_summary(observed, doc)
                _job_update(job_id, phase='verification', state='warning', containers=observed,
                            message='Mindestens ein Container scheitert dauerhaft. ' + diagnosis,
                            events='Neustartschleife erkannt; Log-Muster lokal ausgewertet, keine Zugangsdaten übertragen.')
                return
            main_container = by_service.get(main_service)
            if main_container:
                if main_created_at is None:
                    main_created_at = time.monotonic()
                # ZimaOS normally starts apps on install. Only request a single
                # start through ZimaOS if the main service remains CREATED/stopped
                # cleanly. Never force-start a crashloop or a non-zero exit.
                if (not attempted_start and time.monotonic() - main_created_at >= 15 and
                        main_container['state'] in ('created', 'exited') and
                        main_container['exit_code'] in (0, None)):
                    attempted_start = True
                    _job_update(job_id, phase='startup', message='App ist gestoppt. Ein Start über ZimaOS wird angefordert.',
                                events='Automatischer Startversuch über ZimaOS.')
                    start_code, start_response = api_call(base, f'/v2/app_management/compose/{urllib.parse.quote(name)}/status',
                                                          'PUT', token, json.dumps('start'))
                    if start_code not in (200, 201, 202, 204):
                        _job_update(job_id, message=f'ZimaOS hat den Start abgelehnt (HTTP {start_code}).',
                                    events='Start fehlgeschlagen: ' + start_response[:160])
            # Report definitive main-service failure early after the image pull.
            if main_container and main_container['state'] in ('exited', 'dead') and main_container['exit_code'] not in (0, None):
                _job_update(job_id, phase='verification', state='warning', containers=observed,
                            message=f"App installiert, {main_service} Exit {main_container['exit_code']}. "
                                    + _im_failure_summary(observed, doc),
                            events='Startfehler des Hauptdienstes. Keine Erfolgsmeldung.')
                return
            time.sleep(2)
        _job_update(job_id, phase='verification', state='warning',
                    message='ZimaOS hat den Auftrag angenommen, aber nicht alle Dienste sind gesund. '
                            + _im_failure_summary(observed, doc),
                    events='Zeitlimit erreicht; Installation nicht als erfolgreich bestätigt.')
    except HTTPException as exc:
        _job_update(job_id, state='error', message=str(exc.detail), events='Installation gestoppt: ' + str(exc.detail))
    except Exception as exc:
        # Do not include exception repr: network libraries may contain credentials.
        _job_update(job_id, state='error', message='Interner Installationsfehler (' + type(exc).__name__ + '). ZimaOS-Logs prüfen.',
                    events='Installationsauftrag konnte nicht vollständig geprüft werden.')


@app.post('/api/install/start')
def start_install(req: Request, payload: Install):
    require_write(req)
    if payload.target_system != "zimaos":
        raise HTTPException(400,"Das gewählte Zielsystem unterstützt derzeit nur den Compose-Export.")
    payload = _install_target(req, payload)
    _validate_install_payload(payload)
    name = slug(str(safe_yaml(payload.compose).get('name', '')))
    owner = str(req.session.get('csrf') or '')
    now = time.monotonic()
    with INSTALL_JOBS_LOCK:
        for key in list(INSTALL_JOBS):
            if INSTALL_JOBS[key]['state'] != 'running' and now - INSTALL_JOBS[key]['updated'] > 1800:
                del INSTALL_JOBS[key]
        if any(j['state'] in ('queued', 'running') and j['name'] == name for j in INSTALL_JOBS.values()):
            raise HTTPException(409, 'Für diese Anwendung läuft bereits eine Installation.')
        if sum(j['state'] in ('queued', 'running') for j in INSTALL_JOBS.values()) >= 2:
            raise HTTPException(429, 'Es laufen bereits zwei Installationsaufträge.')
        job_id = secrets.token_urlsafe(24)
        INSTALL_JOBS[job_id] = {'id': job_id, 'owner': owner, 'name': name, 'state': 'queued',
                               'phase': 'preflight', 'message': 'Installation wird vorbereitet.',
                               'events': [], 'containers': [], 'accepted': False, 'updated': now}
    try:
        INSTALL_EXECUTOR.submit(_job_worker, job_id, payload)
    except RuntimeError:
        with INSTALL_JOBS_LOCK:
            INSTALL_JOBS.pop(job_id, None)
        raise HTTPException(503, 'Installationsdienst momentan nicht verfügbar.')
    return {'job_id': job_id, 'name': name}


@app.get('/api/install/jobs/{job_id}')
def installation_job(req: Request, job_id: str):
    require_auth(req)
    with INSTALL_JOBS_LOCK:
        job = INSTALL_JOBS.get(job_id)
        if not job or not hmac.compare_digest(job['owner'], str(req.session.get('csrf') or '')):
            raise HTTPException(404, 'Installationsauftrag nicht gefunden.')
        return {key: job[key] for key in ('id', 'name', 'state', 'phase', 'message', 'events', 'containers', 'accepted')}


@app.post("/api/check")
def check(req: Request, payload: Check):
    require_write(req)
    name = slug(payload.name)
    base = _check_target(payload.host, payload.internal_host)
    token = zima_login(base, payload.username, payload.password)
    code, raw = api_call(base, f"/v2/app_management/compose/{name}/containers", "GET", token=token)
    if code != 200:
        return {"verified": False, "code": code, "message": "Container noch nicht verfügbar"}
    try:
        state = json.loads(raw)
    except ValueError:
        state = {"raw": raw[:600]}
    return {"verified": True, "containers": state}
