# SPDX-License-Identifier: GPL-3.0-only
"""Beta 18: pasted Docker service fragments get safe Compose structure."""
import os
import unittest
from unittest.mock import patch
import yaml

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-use-on-nas')
import main as im  # noqa: E402


class Beta18FragmentImportTests(unittest.TestCase):
    FRAGMENT = """mkvpriority:
  image: ghcr.io/kennethsible/mkvpriority
  container_name: mkvpriority
  user: 1000:1000
  environment:
    WEBHOOK_PORT: "8080"
    MKVPRIORITY_ARGS: >-
      --archive /config/archive.db
  volumes:
    - /path/to/media:/media:ro
    - /path/to/mkvpriority/config:/config
  ports:
    - "8989:8989"
sonarr:
  image: lscr.io/linuxserver/sonarr
  volumes:
    - /path/to/media:/media
    - /path/to/sonarr/config:/config
networks:
  media_net: {}
volumes:
  cache: {}
"""

    def test_two_service_fragment_gets_services_wrapper(self):
        changed, notes = im._im_normalize_pasted_service_fragment(self.FRAGMENT)
        doc = im.safe_yaml(changed)
        self.assertEqual(set(doc['services']), {'mkvpriority', 'sonarr'})
        self.assertEqual(doc['services']['mkvpriority']['volumes'][0],
                         '/path/to/media:/media:ro')
        self.assertEqual(doc['services']['mkvpriority']['user'], '1000:1000')
        self.assertEqual(doc['services']['mkvpriority']['environment']['WEBHOOK_PORT'], '8080')
        self.assertEqual(doc['networks'], {'media_net': {}})
        self.assertEqual(doc['volumes'], {'cache': {}})
        self.assertTrue(any('services:' in note for note in notes))

    def test_analyze_source_returns_actionable_yaml_and_explains_repair(self):
        result = im._analyze_source_payload(im.Source(kind='yaml', value=self.FRAGMENT))
        doc = im.safe_yaml(result['source'])
        self.assertEqual(result['automation']['service_count'], 2)
        self.assertEqual(set(doc['services']), {'mkvpriority', 'sonarr'})
        self.assertTrue(any('automatisch ergänzt' in note for note in result['notes']))
        self.assertEqual(doc['services']['mkvpriority']['volumes'][1],
                         '/path/to/mkvpriority/config:/config')

    def test_repaired_fragment_still_uses_beta17_nas_mount_resolution(self):
        analyzed = im._analyze_source_payload(im.Source(kind='yaml', value=self.FRAGMENT))
        with patch.object(im, '_im_existing_nas_media_sources',
                          return_value={'/DATA/Media'}), \
             patch.object(im, 'require_ports_free',
                          return_value={'ports': [], 'blocked': False}), \
             patch.object(im, '_im_external_network_issues', return_value=[]):
            result = im.build_plan(im.Plan(source=analyzed['source'],
                                           name='mkvpriority', title='MKVPriority'))
        doc = im.safe_yaml(result['compose'])
        self.assertTrue(result['install_ready'], result['setup_issues'])
        self.assertEqual(doc['services']['mkvpriority']['volumes'][0],
                         '/DATA/Media:/media:ro')
        self.assertEqual(doc['services']['sonarr']['volumes'][0],
                         '/DATA/Media:/media')
        self.assertEqual(doc['services']['mkvpriority']['volumes'][1],
                         '/DATA/AppData/mkvpriority/mkvpriority/config:/config')
        self.assertEqual(doc['services']['sonarr']['volumes'][1],
                         '/DATA/AppData/mkvpriority/sonarr/config:/config')

    def test_complete_compose_is_unchanged(self):
        full = 'services:\n  app:\n    image: nginx:alpine\n    volumes:\n      - /DATA/Media:/media:ro\n'
        fixed, notes = im._im_normalize_pasted_service_fragment(full)
        self.assertEqual(fixed, full)
        self.assertEqual(notes, [])

    def test_unknown_top_level_key_never_auto_repaired(self):
        partial = 'app:\n  image: nginx:alpine\nunknown:\n  value: hello\n'
        fixed, notes = im._im_normalize_pasted_service_fragment(partial)
        self.assertEqual(fixed, partial)
        self.assertEqual(notes, [])

    def test_missing_image_not_guessed(self):
        partial = 'app:\n  volumes:\n    - /DATA/app:/data\n'
        fixed, notes = im._im_normalize_pasted_service_fragment(partial)
        self.assertEqual((fixed, notes), (partial, []))

    def test_only_service_body_does_not_gain_guessed_name(self):
        partial = 'image: nginx:alpine\nrestart: always\n'
        fixed, notes = im._im_normalize_pasted_service_fragment(partial)
        self.assertEqual((fixed, notes), (partial, []))

    def test_explicit_empty_services_not_accepted(self):
        partial = 'services: {}\napp:\n  image: nginx:alpine\n'
        fixed, notes = im._im_normalize_pasted_service_fragment(partial)
        self.assertEqual((fixed, notes), (partial, []))
        with self.assertRaises(im.HTTPException):
            im.safe_yaml(fixed)

    def test_malformed_yaml_does_not_silently_change(self):
        source = 'app:\n  image: [bad\n'
        fixed, notes = im._im_normalize_pasted_service_fragment(source)
        self.assertEqual((fixed, notes), (source, []))

    def test_repeat_normalization_is_idempotent(self):
        changed, notes = im._im_normalize_pasted_service_fragment(self.FRAGMENT)
        twice, notes2 = im._im_normalize_pasted_service_fragment(changed)
        self.assertTrue(notes)
        self.assertEqual((twice, notes2), (changed, []))


if __name__ == '__main__':
    unittest.main()
