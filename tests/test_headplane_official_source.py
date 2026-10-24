# SPDX-License-Identifier: GPL-3.0-only
"""Use publisher's Headplane installer instead of its local developer stack."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-use-on-nas')

import main as im  # noqa: E402


DEVELOPER_SOURCE = """# THIS IS A DEVELOPER CONFIGURATION FILE
# IT IS NOT AN EXAMPLE OF SOMETHING YOU DEPLOY
# I ONLY USE IT FOR DEVELOPING HEADPLANE
networks:
  headplane-dev:
    driver: bridge
services:
  caddy:
    image: caddy:2
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    ports:
      - "80:80"
  headscale:
    image: headscale/headscale:0.29.2
    volumes:
      - ./test:/etc/headscale
"""


class HeadplaneOfficialSourceTests(unittest.TestCase):
    def test_repository_selection_does_not_scan_developer_compose(self):
        with patch.object(im, '_github_json') as github, \
             patch.object(im, '_download_remote') as downloader:
            content, url, notes = im._discover_github_repository(['tale', 'headplane'])
        github.assert_not_called()
        downloader.assert_not_called()
        doc = im.safe_yaml(content)
        self.assertEqual(set(doc['services']), {'headplane'})
        self.assertEqual(doc['services']['headplane']['image'],
                         'ghcr.io/tale/headplane:latest')
        self.assertNotIn('headplane-dev', content)
        self.assertNotIn('caddy', doc['services'])
        self.assertEqual(url, 'https://headplane.net/install/docker')
        self.assertTrue(any('config.yaml' in n for n in notes))

    def test_publishers_exact_required_bind_mounts(self):
        content, url, _ = im._publisher_template('tale', 'headplane')
        doc = im.safe_yaml(content)
        self.assertEqual(doc['x-casaos']['main'], 'headplane')
        self.assertEqual(doc['x-casaos']['port_map'], '3000')
        service = doc['services']['headplane']
        self.assertEqual(service['ports'], ['3000:3000'])
        self.assertEqual(service['volumes'][0]['source'],
                         '/DATA/AppData/$AppID/config.yaml')
        self.assertEqual(service['volumes'][0]['target'],
                         '/etc/headplane/config.yaml')
        self.assertTrue(service['volumes'][0]['read_only'])
        self.assertEqual(service['volumes'][1]['target'], '/var/lib/headplane')
        self.assertFalse(any('headscale/headscale' in str(s) for s in
                             doc['services'].values()))

    def test_preview_maps_appid_and_keeps_config_file_gate(self):
        source, _, _ = im._publisher_template('tale', 'headplane')
        with patch.object(im, 'require_ports_free',
                          return_value={'ports': [], 'blocked': False}), \
             patch.object(im, '_im_host_file_mount_issues',
                          return_value=['headplane: Datei-Mount /DATA/AppData/headplane/config.yaml existiert nicht.']), \
             patch.object(im, '_im_external_network_issues', return_value=[]):
            result = im.build_plan(im.Plan(source=source,
                    name='headplane', title='Headplane'))
        doc = im.safe_yaml(result['compose'])
        volume = doc['services']['headplane']['volumes']
        self.assertEqual(volume[0]['source'],
                         '/DATA/AppData/headplane/config.yaml')
        self.assertEqual(volume[1]['source'], '/DATA/AppData/headplane/data')
        self.assertEqual(result['main'], 'headplane')
        self.assertFalse(result['install_ready'])
        self.assertTrue(any('config.yaml' in issue for issue in result['setup_issues']))

    def test_direct_developer_compose_rejected_not_installed(self):
        with self.assertRaises(im.HTTPException) as caught:
            im._analyze_source_payload(im.Source(kind='yaml', value=DEVELOPER_SOURCE))
        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn('nur für die Entwicklung', caught.exception.detail)
        self.assertIn('https://github.com/tale/headplane', caught.exception.detail)

    def test_direct_github_file_rejected(self):
        with patch.object(im, 'discover_source', return_value=(
                DEVELOPER_SOURCE,
                'https://raw.githubusercontent.com/tale/headplane/main/compose.yaml',
                [])):
            with self.assertRaises(im.HTTPException) as caught:
                im._analyze_source_payload(im.Source(
                    kind='url',
                    value='https://github.com/tale/headplane/blob/main/compose.yaml'))
        self.assertEqual(caught.exception.status_code, 422)

    def test_unrelated_compose_keeps_existing_behavior(self):
        ordinary = ("services:\n  caddy:\n    image: caddy:2\n"
                    "    volumes:\n      - ./Caddyfile:/etc/caddy/Caddyfile\n")
        with patch.object(im, 'discover_source') as finder:
            doc = im.safe_yaml(ordinary)
        self.assertEqual(doc['services']['caddy']['image'], 'caddy:2')
        finder.assert_not_called()


if __name__ == '__main__':
    unittest.main()
