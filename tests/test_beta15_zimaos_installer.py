# SPDX-License-Identifier: GPL-3.0-only
"""Beta 15 regressions for native ZimaOS deployments and install preflight."""
import os
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-use-on-nas')

import main as im  # noqa: E402


class Beta15NativeZimaOSTests(unittest.TestCase):
    OFFICIAL = """name: nametag
services:
  nametag:
    image: ghcr.io/mattogodoy/nametag:0.64.0
    ports:
      - "10300:3000"
    volumes:
      - type: bind
        source: /DATA/AppData/$AppID/data
        target: /app/data
    depends_on:
      nametag-init:
        condition: service_completed_successfully
  nametag-init:
    image: alpine:3.20
    restart: "no"
    volumes:
      - type: bind
        source: /DATA/AppData/$AppID/data
        target: /data
    command:
      - /bin/sh
      - -c
      - 'echo $$CRON_SECRET'
networks:
  nametag:
    name: nametag
x-casaos:
  main: nametag
  port_map: "10300"
"""

    GENERIC = """services:
  db:
    image: postgres:16-alpine
  app:
    image: ghcr.io/mattogodoy/nametag:latest
    depends_on:
      - db
    networks:
      - proxy
networks:
  proxy:
    external: true
"""

    def test_publisher_native_bundle_outscores_generic_root(self):
        path = 'deploy/zimaos/Nametag/docker-compose.yml'
        self.assertTrue(im._im_official_zimaos_path(path, 'nametag'))
        self.assertGreater(im._github_deploy_score(path, 'nametag'),
                           im._github_deploy_score('docker-compose.yml', 'nametag'))
        self.assertFalse(im._im_official_zimaos_path(
            'deploy/zimaos/Unrelated/docker-compose.yml', 'nametag'))

    def test_repository_prefers_verified_native_bundle(self):
        examined = []
        def download(url, max_bytes=524288):
            examined.append(url)
            if url.endswith('/deploy/zimaos/Nametag/docker-compose.yml'):
                return self.OFFICIAL
            if url.endswith('/docker-compose.yml'):
                return self.GENERIC
            raise im.HTTPException(404, 'fixture unavailable')

        with patch.object(im, '_github_json', return_value={'default_branch':'master', 'size':100}), \
             patch.object(im, '_github_repository_files', return_value=(
                 {'docker-compose.yml', 'deploy/zimaos/Nametag/docker-compose.yml'}, False)), \
             patch.object(im, '_download_remote', side_effect=download):
            source, url, notes = im._discover_github_repository(['mattogodoy', 'nametag'])
        self.assertEqual(source, self.OFFICIAL)
        self.assertTrue(url.endswith('deploy/zimaos/Nametag/docker-compose.yml'))
        self.assertTrue(any('deploy/zimaos/Nametag' in note for note in notes))

    def test_appid_sources_resolve_without_touching_shell_variables(self):
        doc = im.safe_yaml(self.OFFICIAL)
        notes = im._im_resolve_zimaos_appid_binds(doc, '/DATA/AppData/nametag')
        self.assertTrue(notes)
        volumes = doc['services']['nametag']['volumes']
        self.assertEqual(volumes[0]['source'], '/DATA/AppData/nametag/data')
        self.assertEqual(doc['services']['nametag-init']['volumes'][0]['source'],
                         '/DATA/AppData/nametag/data')
        self.assertIn('$$CRON_SECRET', doc['services']['nametag-init']['command'][2])

    def test_external_network_missing_is_blocked_before_post(self):
        doc = im.safe_yaml(self.GENERIC)
        with patch.object(im.subprocess, 'run',
                          return_value=SimpleNamespace(returncode=1, stdout='', stderr='not found')):
            problems = im._im_external_network_issues(doc)
        self.assertEqual(len(problems), 1)
        self.assertIn('proxy', problems[0])
        self.assertIn('fehlt', problems[0])

    def test_external_network_present_is_ok(self):
        doc = im.safe_yaml(self.GENERIC)
        with patch.object(im.subprocess, 'run',
                          return_value=SimpleNamespace(returncode=0, stdout='proxy\n', stderr='')):
            self.assertEqual(im._im_external_network_issues(doc), [])

    def test_no_external_network_is_not_checked(self):
        doc = im.safe_yaml(self.OFFICIAL)
        with patch.object(im.subprocess, 'run') as run:
            self.assertEqual(im._im_external_network_issues(doc), [])
            run.assert_not_called()

    def test_init_container_exit_zero_counts_as_success(self):
        services = {
            'nametag-init': {'image': 'alpine:3.20', 'restart': 'no'},
            'app': {'image': 'ghcr.io/mattogodoy/nametag:0.64.0',
                    'depends_on': {'nametag-init': {'condition': 'service_completed_successfully'}}},
        }
        observed = [
            {'service': 'nametag-init', 'state': 'exited', 'health': '', 'exit_code': 0},
            {'service': 'app', 'state': 'running', 'health': '', 'exit_code': 0},
        ]
        ok, explanation, _ = im._check_runtime(services, 'app', observed)
        self.assertTrue(ok, explanation)
        observed[0]['exit_code'] = 1
        ok, _, _ = im._check_runtime(services, 'app', observed)
        self.assertFalse(ok)

    def test_do_not_auto_create_external_network(self):
        doc = im.safe_yaml(self.GENERIC)
        with patch.object(im.subprocess, 'run',
                          side_effect=FileNotFoundError()):
            problems = im._im_external_network_issues(doc)
        self.assertTrue(any('nicht prüfbar' in issue for issue in problems))


if __name__ == '__main__':
    unittest.main()
