# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests for source-import WebUI inference and conflict checks."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-use-on-nas')

import main as im  # noqa: E402


def example(**overrides):
    svc = {
        'image': 'ghcr.io/example/web:latest',
        'healthcheck': {
            'test': ['CMD-SHELL', 'curl -f http://127.0.0.1:3000/health || exit 1']
        },
        'expose': ['3000/tcp'],
    }
    svc.update(overrides)
    return {'name': 'webapp', 'services': {'webapp': svc}}


class VerifiedPortCompletionTests(unittest.TestCase):
    def test_one_proven_web_port_gets_host_mapping(self):
        doc = example()
        notes = im._im_autocomplete_verified_web_port(doc, 'webapp')
        self.assertEqual(doc['services']['webapp']['ports'], ['3000:3000'])
        self.assertEqual(doc['x-casaos']['port_map'], '3000')
        self.assertEqual(doc['x-casaos']['main'], 'webapp')
        self.assertEqual(len(notes), 1)

    def test_existing_casaos_host_port_is_honored(self):
        doc = example()
        doc['x-casaos'] = {'main': 'webapp', 'port_map': '3459'}
        im._im_autocomplete_verified_web_port(doc, 'webapp')
        self.assertEqual(doc['services']['webapp']['ports'], ['3459:3000'])

    def test_never_invent_port_from_expose_only(self):
        doc = example(healthcheck={})
        self.assertEqual(im._im_autocomplete_verified_web_port(doc, 'webapp'), [])
        self.assertNotIn('ports', doc['services']['webapp'])
        self.assertNotIn('x-casaos', doc)

    def test_unknown_port_and_remote_health_url_remain_closed(self):
        for health in (
            {'test': ['CMD-SHELL', 'wget http://example.test:3000/health']},
            {'test': ['CMD-SHELL', 'curl -f http://localhost:3000/health && curl -f http://localhost:3001/health']},
            {},
        ):
            doc = example(healthcheck=health, expose=['3000'])
            with self.subTest(health=health):
                self.assertFalse(im._im_autocomplete_verified_web_port(doc, 'webapp'))
                self.assertNotIn('ports', doc['services']['webapp'])

    def test_expose_must_agree_with_http_healthcheck(self):
        for expose in (['3001'], ['3000/udp'], ['3000', '3001'], ['not-a-port']):
            doc = example(expose=expose)
            with self.subTest(expose=expose):
                self.assertEqual(im._im_autocomplete_verified_web_port(doc, 'webapp'), [])
                self.assertNotIn('ports', doc['services']['webapp'])

    def test_never_touch_declared_port_or_host_network(self):
        for overrides in (
            {'ports': ['3001:3000']},
            {'ports': []},
            {'network_mode': 'host'},
            {'profiles': ['test']},
        ):
            doc = example(**overrides)
            original = im.yaml.safe_dump(doc)
            self.assertFalse(im._im_autocomplete_verified_web_port(doc, 'webapp'))
            self.assertEqual(im.yaml.safe_dump(doc), original)

    def test_reverse_proxy_only_service_is_never_exposed(self):
        for changes in (
            {'labels': {'traefik.enable': 'true',
                        'traefik.http.routers.web.rule': 'Host(web.example.test)'}},
            {'labels': ['caddy=web.example.test']},
            {'deploy': {'labels': ['traefik.http.services.web.loadbalancer.server.port=3000']}},
        ):
            doc = example(**changes)
            with self.subTest(changes=changes):
                self.assertFalse(im._im_autocomplete_verified_web_port(doc, 'webapp'))
                self.assertNotIn('ports', doc['services']['webapp'])

    def test_no_auto_exposure_of_infrastructure_and_ambiguous_stacks(self):
        doc = example(image='postgres:17')
        self.assertFalse(im._im_autocomplete_verified_web_port(doc, 'webapp'))
        doc = {'name': 'project', 'services': {
            'first': example()['services']['webapp'],
            'second': {'image': 'redis:8'},
        }}
        self.assertFalse(im._im_autocomplete_verified_web_port(doc, 'project'))

    def test_explicit_main_in_multi_service_stack(self):
        doc = {'name': 'group', 'x-casaos': {'main': 'webui'},
               'services': {'redis': {'image': 'redis:8'},
                            'webui': example()['services']['webapp']}}
        self.assertTrue(im._im_autocomplete_verified_web_port(doc, 'group'))
        self.assertEqual(doc['services']['webui']['ports'], ['3000:3000'])
        self.assertNotIn('ports', doc['services']['redis'])

    def test_import_yaml_with_proven_http_port_gets_usable_compose(self):
        upstream = im.yaml.safe_dump(example())
        with patch.object(im, '_project_info', return_value=('', '', [])):
            res = im._analyze_source_payload(im.Source(kind='yaml', value=upstream))
        doc = im.safe_yaml(res['source'])
        self.assertEqual(doc['services']['webapp']['ports'], ['3000:3000'])
        self.assertTrue(any('Healthcheck' in n for n in res['notes']))

    def test_url_source_checks_conflicts_unlike_pasted_manual_yaml(self):
        data = im.yaml.safe_dump({
            'services': {'web': {
                'image': 'example/web:latest', 'ports': ['8080:3000']}}})
        with patch.object(im, 'discover_source', return_value=(
                data, 'https://example.test/compose.yml', [])), \
             patch.object(im, '_project_info', return_value=('', '', [])), \
             patch.object(im, '_published_images_in_readme', return_value=[]), \
             patch.object(im, '_auto_reassign_conflicting_ports', return_value=[]) as reroute:
            im._analyze_source_payload(im.Source(
                kind='url', value='https://example.test/compose.yml'))
        reroute.assert_called_once()
        with patch.object(im, '_auto_reassign_conflicting_ports') as reroute:
            im._analyze_source_payload(im.Source(kind='yaml', value=data))
        reroute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
