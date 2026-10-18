#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Fail-closed source-package prepublish checks; not a full secret scanner."""
from __future__ import annotations
import ipaddress
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
TEXT_EXT={'.py','.js','.css','.html','.md','.txt','.yml','.yaml','.sh','.json','.example','.svg','.gitignore','.dockerignore'}
TEXT_NAMES={'.gitignore','.dockerignore','Dockerfile','install.sh','requirements.txt'}
FORBIDDEN_NAMES={'.env','install-monitor.env'}
FORBIDDEN_DIRS={'data','registry','tmp','backups','cache','logs'}
LOCAL_IGNORED_DIRS={'.git','.venv','__pycache__','.pytest_cache'}
FINDINGS=[]
PATTERNS={
 'GitHub personal access token':re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{25,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
 'Possible provider API key':re.compile(r'\b(?:sk-proj-|sk_live_|AIza)[A-Za-z0-9_-]{25,}\b'),
 'Private SSH key':re.compile(r'-----BEGIN (?:OPENSSH|RSA|EC|DSA|PRIVATE) PRIVATE KEY-----'),
 'Embedded dotenv credentials':re.compile(r'(?m)^\s*(?:IM_SESSION_SECRET|IM_ADMIN_PASSWORD_HASH|IM_ADMIN_PASSWORD)=(?!REPLACE_|CHANGE_ME_)[^\n#\s]{24,}\s*$'),
}
IP_RE=re.compile(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])')
ALLOW_EXAMPLE={'10.0.0.0','172.16.0.0','192.168.0.0','127.0.0.1','127.0.0.0','0.0.0.0'}

for p in ROOT.rglob('*'):
 if p.is_symlink():
  FINDINGS.append(f'Symlink verboten: {p.relative_to(ROOT)}');continue
 rel=p.relative_to(ROOT)
 if any(component in LOCAL_IGNORED_DIRS for component in rel.parts):continue
 if p.is_dir():
  if p.name in FORBIDDEN_DIRS:FINDINGS.append(f'Laufzeitordner enthalten: {rel}')
  continue
 if p.name in FORBIDDEN_NAMES or p.suffix in {'.key','.pem','.p12','.pfx','.zip','.tar','.db','.sqlite'}:
  FINDINGS.append(f'Private oder unzulässige Datei: {rel}')
 if p.suffix not in TEXT_EXT and p.name not in TEXT_NAMES:continue
 if rel.as_posix()=='scripts/prepublish_check.py':continue
 try: text=p.read_text(encoding='utf-8')
 except UnicodeDecodeError:FINDINGS.append(f'Nicht lesbare Textdatei: {rel}');continue
 for title,pat in PATTERNS.items():
  for match in pat.finditer(text):FINDINGS.append(f'{title} in {rel} Zeile {text.count(chr(10),0,match.start())+1}')
 for match in IP_RE.finditer(text):
  ip=match.group(0)
  try:obj=ipaddress.IPv4Address(ip)
  except ipaddress.AddressValueError:continue
  if obj.is_private and ip not in ALLOW_EXAMPLE:
   FINDINGS.append(f'Private IPv4-Adresse in {rel} Zeile {text.count(chr(10),0,match.start())+1}: {ip}')
if FINDINGS:
 print('VERÖFFENTLICHUNG GESPERRT:')
 for item in FINDINGS:print(' -',item)
 sys.exit(1)
print('OK: Keine erkannten privaten Runtime-Dateien, Secrets oder unzulässigen privaten IPv4-Adressen.')
