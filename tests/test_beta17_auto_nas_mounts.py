# SPDX-License-Identifier: GPL-3.0-only
"""Beta 17: manufacturer sample mounts are resolved conservatively and shared."""
import os
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-use-on-nas')

import main as im  # noqa: E402


class Beta17AutoNASMountTests(unittest.TestCase):
    SOURCE = """
services:
  sonarr:
    image: lscr.io/linuxserver/sonarr:latest
    volumes:
      - /path/to/media:/media:ro
      - /path/to/sonarr/config:/config
      - /path/to/mkvpriority/config:/mkvpriority
    ports:
      - "8989:8989"
  mkvpriority:
    image: example/mkvpriority:latest
    volumes:
      - /path/to/media:/media
      - /path/to/mkvpriority/config:/config
"""

    def test_unique_media_mount_and_isolated_config_folders(self):
        doc = im.safe_yaml(self.SOURCE)
        with patch.object(im, '_im_existing_nas_media_sources',
                          return_value={'/DATA/Filme/Medien'}) as probe:
            notes = im._im_auto_resolve_example_mounts(
                doc, 'mkvpriority', '/DATA/AppData/mkvpriority')
        probe.assert_called_once()
        sonarr = doc['services']['sonarr']['volumes']
        worker = doc['services']['mkvpriority']['volumes']
        self.assertEqual(sonarr, [
            '/DATA/Filme/Medien:/media:ro',
            '/DATA/AppData/mkvpriority/sonarr/config:/config',
            '/DATA/AppData/mkvpriority/mkvpriority/config:/mkvpriority'])
        self.assertEqual(worker, [
            '/DATA/Filme/Medien:/media',
            '/DATA/AppData/mkvpriority/mkvpriority/config:/config'])
        self.assertFalse(im._im_sample_mount_issues(doc))
        self.assertTrue(any('Gemeinsamer Medienordner' in n for n in notes))
        # Idempotent after the conversion: no paths get replaced again.
        with patch.object(im, '_im_existing_nas_media_sources') as probe:
            self.assertEqual(im._im_auto_resolve_example_mounts(
                doc, 'mkvpriority', '/DATA/AppData/mkvpriority'), [])
        probe.assert_not_called()

    def test_ambiguous_media_remains_one_actionable_error(self):
        doc = im.safe_yaml(self.SOURCE)
        with patch.object(im, '_im_existing_nas_media_sources',
                          return_value={'/DATA/Medien', '/media/Movies'}):
            im._im_auto_resolve_example_mounts(doc, 'mkvpriority',
                                               '/DATA/AppData/mkvpriority')
        issues = im._im_sample_mount_issues(doc)
        self.assertEqual(len(issues), 1)
        self.assertIn('Gemeinsamer Medienordner', issues[0])
        self.assertIn('sonarr', issues[0])
        self.assertIn('mkvpriority', issues[0])
        self.assertIn('/path/to/media', doc['services']['sonarr']['volumes'][0])

    def test_no_media_does_not_invent_or_create_one(self):
        doc = im.safe_yaml(self.SOURCE)
        with patch.object(im, '_im_existing_nas_media_sources', return_value=set()):
            notes = im._im_auto_resolve_example_mounts(
                doc, 'mkvpriority', '/DATA/AppData/mkvpriority')
        self.assertTrue(any('keine eindeutige' in n for n in notes))
        self.assertEqual(len(im._im_sample_mount_issues(doc)), 1)

    def test_file_mount_and_explicit_mount_unchanged(self):
        doc = {'services': {'app': {'image': 'example/app',
               'volumes': ['/path/to/app/settings.yml:/etc/app/settings.yml',
                           '/DATA/Media:/media:ro',
                           'named_volume:/cache',
                           {'type': 'bind', 'source': '/path/to/app/config',
                            'target': '/config', 'read_only': True}]}}}
        with patch.object(im, '_im_existing_nas_media_sources') as probe:
            im._im_auto_resolve_example_mounts(doc, 'app', '/DATA/AppData/app')
        probe.assert_not_called()
        volumes = doc['services']['app']['volumes']
        self.assertEqual(volumes[:3], [
            '/path/to/app/settings.yml:/etc/app/settings.yml',
            '/DATA/Media:/media:ro', 'named_volume:/cache'])
        self.assertEqual(volumes[3], {'type': 'bind',
                         'source': '/DATA/AppData/app/app/config',
                         'target': '/config', 'read_only': True})
        self.assertEqual(len(im._im_sample_mount_issues(doc)), 1)

    def test_unknown_custom_base_does_not_create_unmanaged_dirs(self):
        doc = im.safe_yaml(self.SOURCE)
        with patch.object(im, '_im_existing_nas_media_sources', return_value=set()):
            im._im_auto_resolve_example_mounts(doc, 'mkvpriority', '/media/unknown')
        self.assertIn('/path/to/sonarr/config', doc['services']['sonarr']['volumes'][1])
        self.assertTrue(im._im_sample_mount_issues(doc))

    def test_nas_directory_candidates_are_bounded_and_verified(self):
        with patch.object(im.subprocess, 'run', return_value=SimpleNamespace(
                returncode=0, stdout='', stderr='')) as run, \
             patch.object(im, '_im_available_media_directory',
                          side_effect=lambda p: p == '/DATA/Media'):
            candidates = im._im_existing_nas_media_sources()
        self.assertEqual(candidates, {'/DATA/Media'})
        self.assertEqual(run.call_count, 1)

    def test_docker_existing_media_metadata_only(self):
        ids = 'a' * 12
        mount_data = [{'Type': 'bind', 'Source': '/DATA/Media',
                       'Destination': '/media'},
                      {'Type': 'bind', 'Source': '/DATA/AppData/sonarr',
                       'Destination': '/config'},
                      {'Type': 'volume', 'Source': 'not-a-host-folder',
                       'Destination': '/media'}]
        def fake_run(args, **kwargs):
            if args[:3] == ['docker', 'ps', '-q']:
                return SimpleNamespace(returncode=0, stdout=ids + '\n', stderr='')
            if args[:3] == ['docker', 'inspect', '--format']:
                return SimpleNamespace(returncode=0, stdout=json.dumps(mount_data) + '\n', stderr='')
            self.fail('Unexpected docker command: ' + repr(args))
        with patch.object(im.subprocess, 'run', side_effect=fake_run) as run, \
             patch.object(im, '_im_available_media_directory',
                          side_effect=lambda p: p == '/DATA/Media'):
            self.assertEqual(im._im_existing_nas_media_sources(), {'/DATA/Media'})
        self.assertEqual(run.call_count, 2)

    def test_user_selected_source_overrides_unrelated_docker_candidates(self):
        doc = im.safe_yaml(self.SOURCE)
        doc['services']['sonarr']['volumes'][0] = '/DATA/SelectedMedia:/media:ro'
        with patch.object(im, '_im_available_media_directory',
                          side_effect=lambda p: p == '/DATA/SelectedMedia'), \
             patch.object(im, '_im_existing_nas_media_sources') as finder:
            im._im_auto_resolve_example_mounts(
                doc, 'mkvpriority', '/DATA/AppData/mkvpriority')
        finder.assert_not_called()
        self.assertEqual(doc['services']['mkvpriority']['volumes'][0],
                         '/DATA/SelectedMedia:/media')

    def test_preview_integrates_auto_resolution_before_setup_validation(self):
        doc = im.safe_yaml(self.SOURCE)
        with patch.object(im, '_im_existing_nas_media_sources',
                          return_value={'/DATA/Media'}), \
             patch.object(im, 'require_ports_free',
                          return_value={'ports': [], 'blocked': False}), \
             patch.object(im, '_im_external_network_issues', return_value=[]):
            result = im.build_plan(im.Plan(source=self.SOURCE,
                                            name='mkvpriority', title='MKVPriority'))
        rendered = im.safe_yaml(result['compose'])
        self.assertTrue(result['install_ready'], result['setup_issues'])
        self.assertEqual(rendered['services']['sonarr']['volumes'][0],
                         '/DATA/Media:/media:ro')
        self.assertEqual(rendered['services']['mkvpriority']['volumes'][0],
                         '/DATA/Media:/media')
        self.assertFalse(im._im_sample_mount_issues(rendered))

    def test_no_placeholders_requires_no_nas_probe(self):
        doc = im.safe_yaml('services:\n  app:\n    image: nginx\n    volumes:\n      - /DATA/Media:/media:ro\n')
        with patch.object(im, '_im_existing_nas_media_sources') as probe:
            self.assertEqual(im._im_auto_resolve_example_mounts(
                doc, 'app', '/DATA/AppData/app'), [])
        probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
