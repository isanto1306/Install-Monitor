# SPDX-License-Identifier: GPL-3.0-only
"""Zimapp-style conversion of fresh, shared Docker volumes into NAS AppData."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-use-on-nas')

import main as im  # noqa: E402


class AppDataNamedVolumesTests(unittest.TestCase):
    def setUp(self):
        self.source = """
name: rssmonster
services:
  rssmonster:
    image: rssmonster/rssmonster:latest
    ports:
      - "3001:3000"
    volumes:
      - rssmonster-data:/app/data
      - rssmonster-worker-health:/app/worker-health:ro
  rssmonster-worker:
    image: rssmonster/rssmonster:latest
    volumes:
      - rssmonster-data:/app/data
      - rssmonster-worker-health:/app/worker-health
  rssmonster-webhook-worker:
    image: rssmonster/rssmonster:latest
    volumes:
      - rssmonster-data:/app/data
volumes:
  rssmonster-data:
  rssmonster-worker-health:
"""

    def _convert(self, source=None, existing=None, base='/DATA/AppData/rssmonster'):
        doc = im.safe_yaml(source or self.source)
        with patch.object(im, '_im_existing_docker_volume_names',
                          return_value=set() if existing is None else existing) as finder:
            notes = im._im_convert_local_named_volumes(doc, 'rssmonster', base)
        return doc, notes, finder

    def test_shared_three_container_rssmonster_layout_and_readonly(self):
        doc, notes, finder = self._convert()
        finder.assert_called_once()
        app = doc['services']['rssmonster']['volumes']
        worker = doc['services']['rssmonster-worker']['volumes']
        webhook = doc['services']['rssmonster-webhook-worker']['volumes']
        self.assertEqual(app[0], {'type': 'bind',
                         'source': '/DATA/AppData/rssmonster/rssmonster-data',
                         'target': '/app/data'})
        self.assertEqual(app[1], {'type': 'bind',
                         'source': '/DATA/AppData/rssmonster/rssmonster-worker-health',
                         'target': '/app/worker-health', 'read_only': True})
        self.assertEqual(worker[0], app[0])
        self.assertEqual(worker[1]['source'], app[1]['source'])
        self.assertNotIn('read_only', worker[1])
        self.assertEqual(webhook[0], app[0])
        self.assertNotIn('volumes', doc)
        self.assertTrue(any('rssmonster-data' in n for n in notes))

    def test_preserves_explicit_binds_and_avoids_directory_collision(self):
        source = """
services:
  app:
    image: busybox
    volumes:
      - /DATA/AppData/rssmonster/cache:/existing
      - cache:/cache:rw
      - cache2:/other
volumes:
  cache: {}
  cache2: {}
"""
        doc, notes, _ = self._convert(source)
        volumes = doc['services']['app']['volumes']
        self.assertEqual(volumes[0], '/DATA/AppData/rssmonster/cache:/existing')
        self.assertEqual(volumes[1]['source'], '/DATA/AppData/rssmonster/cache-2')
        self.assertEqual(volumes[2]['source'], '/DATA/AppData/rssmonster/cache2')
        self.assertNotIn('read_only', volumes[1])

    def test_existing_volume_is_not_replaced_without_migration(self):
        doc, notes, _ = self._convert(existing={'rssmonster_rssmonster-data'})
        app_volumes = doc['services']['rssmonster']['volumes']
        self.assertEqual(app_volumes[0], 'rssmonster-data:/app/data')
        self.assertEqual(app_volumes[1]['type'], 'bind')
        self.assertIn('rssmonster-data', doc['volumes'])
        self.assertNotIn('rssmonster-worker-health', doc['volumes'])
        self.assertTrue(any('existiert bereits' in note for note in notes))

    def test_failed_docker_inspection_preserves_all_data(self):
        with patch.object(im, '_im_existing_docker_volume_names', return_value=None):
            original = im.safe_yaml(self.source)
            warnings = im._im_convert_local_named_volumes(
                original, 'rssmonster', '/DATA/AppData/rssmonster')
        self.assertEqual(original['services']['rssmonster']['volumes'][0],
                         'rssmonster-data:/app/data')
        self.assertEqual(len(original['volumes']), 2)
        self.assertTrue(any('nicht überprüft' in note for note in warnings))

    def test_external_and_driver_opts_preserved(self):
        source = """
services:
  app:
    image: busybox
    volumes:
      - outside:/external
      - special:/special
      - data:/data
volumes:
  outside:
    external: true
  special:
    driver: local
    driver_opts:
      type: nfs
      o: addr=127.0.0.1
      device: :/share
  data: {}
"""
        doc, notes, _ = self._convert(source)
        self.assertEqual(doc['services']['app']['volumes'][0], 'outside:/external')
        self.assertEqual(doc['services']['app']['volumes'][1], 'special:/special')
        self.assertEqual(doc['services']['app']['volumes'][2]['type'], 'bind')
        self.assertEqual(set(doc['volumes']), {'outside', 'special'})
        self.assertTrue(any('Spezielle oder externe' in n for n in notes))

    def test_long_form_mount_and_nocopy_is_preserved(self):
        source = """
services:
  app:
    image: busybox
    volumes:
      - type: volume
        source: data
        target: /data
        read_only: true
      - type: volume
        source: nocopy
        target: /nocopy
        volume:
          nocopy: true
volumes:
  data: {}
  nocopy: {}
"""
        doc, _, _ = self._convert(source)
        app = doc['services']['app']['volumes']
        self.assertEqual(app[0], {'type': 'bind',
                         'source': '/DATA/AppData/rssmonster/data',
                         'target': '/data', 'read_only': True})
        self.assertEqual(app[1]['type'], 'volume')
        self.assertIn('nocopy', doc['volumes'])

    def test_unsupported_short_mount_options_remain_as_named_volume(self):
        source = """
services:
  app:
    image: busybox
    volumes:
      - data:/data:ro,z
volumes:
  data: {}
"""
        doc, notes, _ = self._convert(source)
        self.assertEqual(doc['services']['app']['volumes'][0],
                         'data:/data:ro,z')
        self.assertIn('data', doc['volumes'])
        self.assertTrue(any('Spezielle Mount-Optionen' in n for n in notes))

    def test_custom_root_outside_app_namespace_is_not_rewritten(self):
        doc, notes, finder = self._convert(base='/media/ssd/app')
        finder.assert_not_called()
        self.assertEqual(doc['services']['rssmonster']['volumes'][0],
                         'rssmonster-data:/app/data')
        self.assertTrue(any('außerhalb' in n for n in notes))

    def test_repeat_conversion_does_not_change_binds(self):
        doc, _, _ = self._convert()
        with patch.object(im, '_im_existing_docker_volume_names') as finder:
            self.assertEqual(im._im_convert_local_named_volumes(
                doc, 'rssmonster', '/DATA/AppData/rssmonster'), [])
        finder.assert_not_called()

    def test_preview_integration_uses_shared_appdata_and_keeps_three_services(self):
        with patch.object(im, '_im_existing_docker_volume_names', return_value=set()), \
             patch.object(im, 'require_ports_free',
                          return_value={'ports': [], 'blocked': False}), \
             patch.object(im, '_im_external_network_issues', return_value=[]):
            result = im.build_plan(im.Plan(source=self.source,
                            name='rssmonster', title='RSSMonster'))
        generated = im.safe_yaml(result['compose'])
        self.assertEqual(len(generated['services']), 3)
        self.assertEqual(generated['services']['rssmonster']['volumes'][0]['source'],
                         '/DATA/AppData/rssmonster/rssmonster-data')
        self.assertEqual(generated['services']['rssmonster-worker']['volumes'][0]['source'],
                         '/DATA/AppData/rssmonster/rssmonster-data')
        self.assertTrue(result['install_ready'], result['setup_issues'])


    def test_shared_appdata_runtime_inspection_detects_wrong_host_paths(self):
        doc, _, _ = self._convert()
        doc['name'] = 'rssmonster'
        shared = im._im_expected_shared_appdata_binds(doc)
        self.assertEqual(len(shared), 2)
        data = '/DATA/AppData/rssmonster/rssmonster-data'
        health = '/DATA/AppData/rssmonster/rssmonster-worker-health'
        self.assertEqual(len(shared[data]), 3)
        self.assertEqual(len(shared[health]), 2)
        observed = [{'service': name, 'id': str(i) * 12}
                    for i, name in enumerate(doc['services'], 1)]
        mounts = {
            '1' * 12: [
                {'Source': data, 'Destination': '/app/data', 'RW': True},
                {'Source': health, 'Destination': '/app/worker-health', 'RW': False}],
            '2' * 12: [
                {'Source': data, 'Destination': '/app/data', 'RW': True},
                {'Source': health, 'Destination': '/app/worker-health', 'RW': True}],
            '3' * 12: [
                {'Source': data, 'Destination': '/app/data', 'RW': True}],
        }
        with patch.object(im, '_im_readonly_mounts',
                          side_effect=lambda ident: mounts[ident]):
            self.assertEqual(im._im_runtime_shared_volume_issues(doc, observed), [])
            mounts['2' * 12][0]['Source'] = '/var/lib/docker/volumes/wrong'
            problems = im._im_runtime_shared_volume_issues(doc, observed)
        self.assertTrue(any('unterschiedliche Host-Datenquellen' in p
                            for p in problems))

    def test_named_volumes_with_driver_opts_never_get_rewritten(self):
        source = """
services:
  app:
    image: busybox
    volumes:
      - special:/data
volumes:
  special:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /DATA/Storage
"""
        doc, notes, finder = self._convert(source)
        finder.assert_not_called()
        self.assertEqual(doc['services']['app']['volumes'][0],
                         'special:/data')
        self.assertIn('special', doc['volumes'])
        self.assertTrue(notes)



if __name__ == '__main__':
    unittest.main()
