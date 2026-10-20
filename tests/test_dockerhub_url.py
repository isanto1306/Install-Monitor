# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests: Docker Hub web links use the existing image workflow."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-only-admin')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-production')

import main as im  # noqa: E402


class DockerHubUrlTests(unittest.TestCase):
    def test_namespaced_image_page(self):
        self.assertEqual(
            im._dockerhub_image_from_url('https://hub.docker.com/r/clamav/clamav'),
            ('clamav/clamav:latest', 'https://hub.docker.com/r/clamav/clamav'))

    def test_official_library_image_page(self):
        self.assertEqual(
            im._dockerhub_image_from_url('https://hub.docker.com/_/nginx/'),
            ('nginx:latest', 'https://hub.docker.com/_/nginx'))
        self.assertEqual(
            im._dockerhub_image_from_url('https://hub.docker.com/r/library/nginx'),
            ('nginx:latest', 'https://hub.docker.com/r/library/nginx'))

    def test_tags_tab_is_not_mistaken_for_a_tag_name(self):
        self.assertEqual(
            im._dockerhub_image_from_url('https://hub.docker.com/r/clamav/clamav/tags'),
            ('clamav/clamav:latest', 'https://hub.docker.com/r/clamav/clamav'))
        with self.assertRaises(im.HTTPException):
            im._dockerhub_image_from_url('https://hub.docker.com/r/clamav/clamav/tags?name=stable')

    def test_bad_urls_are_rejected_without_visiting_them(self):
        for link in (
            'http://hub.docker.com/r/clamav/clamav',
            'https://hub.docker.com:8080/r/clamav/clamav',
            'https://user:pass@hub.docker.com/r/clamav/clamav',
            'https://hub.docker.com/r/clamav',
            'https://hub.docker.com/r/clamav/clamav/extra',
            'https://hub.docker.com/r/../clamav',
            'https://hub.docker.com/r/clamav/clamav?token=abcd',
        ):
            with self.subTest(link=link):
                with self.assertRaises(im.HTTPException):
                    im._dockerhub_image_from_url(link)
        self.assertIsNone(im._dockerhub_image_from_url(
            'https://hub.docker.com.evil.example/r/clamav/clamav'))

    def test_clamav_metadata_draft_stays_off_host_network(self):
        draft = {
            'services': {
                'clamav': {
                    'image': 'clamav/clamav:latest',
                    'ports': ['3310:3310', '127.0.0.1:12345:12345/tcp']
                }
            }
        }
        notes = im._dockerhub_url_safe_draft(draft, 'clamav/clamav:latest')
        self.assertEqual(
            draft['services']['clamav']['ports'],
            ['127.0.0.1:12345:12345/tcp'])
        self.assertTrue(any('3310' in note for note in notes))

    def test_other_images_are_unaffected(self):
        doc = {'services': {'web': {'image': 'someuser/someapp:latest',
                                      'ports': ['3310:3310']}}}
        self.assertEqual(im._dockerhub_url_safe_draft(doc, 'someuser/someapp:latest'), [])
        self.assertEqual(doc['services']['web']['ports'], ['3310:3310'])

    def test_composite_analyzer_routes_dockerhub_link_through_image_documentation(self):
        publisher_compose = (
            'services:\n'
            '  clamav:\n'
            '    image: clamav/clamav:latest\n'
            '    ports:\n'
            '      - "3310:3310"\n'
            '    volumes:\n'
            '      - "/DATA/AppData/clamav/db:/var/lib/clamav"\n'
        )
        link = 'https://hub.docker.com/r/clamav/clamav'
        with (patch.object(im, '_public_remote', side_effect=lambda u: u) as check,
              patch.object(im, '_dockerhub_publisher_documentation', return_value=(
                  publisher_compose, 'https://hub.docker.com/v2/repositories/clamav/clamav/',
                  link, ['Herstellerinformationen erkannt'])) as docs,
              patch.object(im, '_im_default_lan_web_port', return_value=[]),
              patch.object(im, '_project_info', return_value=(link, '', [])),
              patch.object(im, '_auto_reassign_conflicting_ports', return_value=[])):
            result = im._analyze_source_payload(im.Source(kind='url', value=link))
        doc = im.safe_yaml(result['source'])
        self.assertEqual(doc['services']['clamav']['image'], 'clamav/clamav:latest')
        self.assertNotIn('ports', doc['services']['clamav'])
        self.assertTrue(doc[im._DOC_IMAGE_PREFLIGHT])
        self.assertEqual(result['project_url'], link)
        self.assertEqual(result['automation']['source_type'], 'url')
        self.assertTrue(any('3310' in note for note in result['notes']))
        docs.assert_called_once_with('clamav/clamav:latest')
        check.assert_called_once_with(link)

    def test_clamav_fallback_has_verified_database_mount_and_no_exposed_tcp(self):
        url = 'https://hub.docker.com/r/clamav/clamav'
        with (patch.object(im, '_public_remote', side_effect=lambda u: u),
              patch.object(im, '_dockerhub_publisher_documentation', return_value=None),
              patch.object(im, '_publisher_compose_for_image', return_value=None),
              patch.object(im, '_im_default_lan_web_port', return_value=[]),
              patch.object(im, '_auto_reassign_conflicting_ports', return_value=[]),
              patch.object(im, 'inspect_remote_image_metadata') as oci):
            result = im._analyze_source_payload(im.Source(kind='url', value=url))
        config = im.safe_yaml(result['source'])
        svc = config['services']['clamav']
        self.assertEqual(svc['image'], 'clamav/clamav:latest')
        self.assertEqual(svc['volumes'], ['/DATA/AppData/clamav/database:/var/lib/clamav'])
        self.assertNotIn('ports', svc)
        self.assertNotIn('x-install-monitor-review-required', config)
        self.assertTrue(config[im._DOC_IMAGE_PREFLIGHT])
        self.assertTrue(any('kein NAS-Ordner' in n for n in result['notes']))
        self.assertEqual(result['automation']['metadata_only'], False)
        self.assertEqual(result['automation']['source_type'], 'url')
        oci.assert_not_called()

    def test_missing_publisher_compose_still_uses_oci_metadata(self):
        link = 'https://hub.docker.com/r/examplevendor/exampleapp'
        metadata = {
            'config': {'ExposedPorts': {'12345/tcp': {}}, 'Volumes': {}},
            'os': 'linux', 'architecture': 'amd64'
        }
        with (patch.object(im, '_public_remote', side_effect=lambda u: u),
              patch.object(im, '_dockerhub_publisher_documentation', return_value=None),
              patch.object(im, '_publisher_compose_for_image', return_value=None),
              patch.object(im, 'inspect_local_image_metadata', return_value=None),
              patch.object(im, 'inspect_remote_image_metadata', return_value=(metadata, '')),
              patch.object(im, '_auto_reassign_conflicting_ports', return_value=[]),
              patch.object(im, '_im_default_lan_web_port', return_value=[])):
            result = im._analyze_source_payload(im.Source(kind='url', value=link))
        document = im.safe_yaml(result['source'])
        self.assertEqual(document['services']['exampleapp']['image'],
                         'examplevendor/exampleapp:latest')
        self.assertEqual(document['services']['exampleapp']['ports'], ['12345:12345/tcp'])
        self.assertTrue(document[im._DOC_IMAGE_PREFLIGHT])
        self.assertEqual(result['automation']['source_type'], 'url')


if __name__ == '__main__':
    unittest.main()
