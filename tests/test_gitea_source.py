# SPDX-License-Identifier: GPL-3.0-only
"""Approved Gitea project and publisher image regression tests."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'testing-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'testing-session-secret-not-for-production')

import main as im  # noqa: E402


class PublicGiteaTests(unittest.TestCase):
    REPO = 'https://gitea.baerentsen.space/FrederikBaerentsen/ComicOPDS'
    MARKDOWN = """# ComicOPDS

```yaml
services:
  comicopds:
    image: gitea.baerentsen.space/frederikbaerentsen/comicopds:latest
    ports:
      - "8382:8080"
    environment:
      CONTENT_BASE_DIR: /library
      SERVER_BASE: "http://192.168.10.10:8382"
    volumes:
      - "./comics:/library:ro"
      - "./data:/data"
```
"""

    def remote(self, url, max_bytes=524288):
        if url.endswith('/api/v1/repos/FrederikBaerentsen/ComicOPDS'):
            return '{"default_branch":"master"}'
        if url.endswith('/raw/branch/master/docs/quickstart.md'):
            return self.MARKDOWN
        raise im.HTTPException(404, 'Not found')

    def test_comicopds_repository_prefers_published_image(self):
        with patch.object(im, '_public_remote', side_effect=lambda value: value), \
             patch.object(im, '_download_remote', side_effect=self.remote):
            content, url, notes = im.discover_source(self.REPO)
        data = im.safe_yaml(content)
        svc = data['services']['comicopds']
        self.assertEqual(svc['image'], 'gitea.baerentsen.space/frederikbaerentsen/comicopds:latest')
        self.assertNotIn('build', svc)
        self.assertEqual(svc['ports'], ['8382:8080'])
        self.assertEqual(svc['environment']['SERVER_BASE'], '$' + '{COMICOPDS_SERVER_BASE}')
        self.assertTrue(data[im._DOC_IMAGE_PREFLIGHT])
        self.assertTrue(url.endswith('docs/quickstart.md'))
        self.assertTrue(any('Hersteller-Image' in note for note in notes))

    def test_repo_project_link_is_preserved(self):
        with patch.object(im, '_public_remote', side_effect=lambda value: value), \
             patch.object(im, '_download_remote', side_effect=self.remote), \
             patch.object(im, '_warnings', return_value=[]), \
             patch.object(im, '_im_default_lan_web_port', return_value=[]):
            result = im._analyze_source_payload(im.Source(kind='url', value=self.REPO))
        self.assertEqual(result['project_url'], self.REPO)
        self.assertEqual(result['name'], 'comicopds')
        self.assertIn('$' + '{COMICOPDS_SERVER_BASE}', result['source'])
        self.assertEqual(result['automation']['service_count'], 1)

    def test_documentation_without_publisher_image_must_not_be_used(self):
        wrong = self.MARKDOWN.replace('gitea.baerentsen.space/frederikbaerentsen/comicopds:latest', 'evil.example/other:latest')
        def response(url, max_bytes=524288):
            if url.endswith('/api/v1/repos/FrederikBaerentsen/ComicOPDS'):
                return '{"default_branch":"master"}'
            if url.endswith('/raw/branch/master/docs/quickstart.md'):
                return wrong
            if url.endswith('/raw/branch/master/compose.yaml'):
                return 'services:\n  comicopds:\n    build: .\n'
            raise im.HTTPException(404, 'missing')
        with patch.object(im, '_download_remote', side_effect=response):
            with self.assertRaises(im.HTTPException) as ctx:
                im._discover_gitea_publisher('gitea.baerentsen.space', 'FrederikBaerentsen', 'ComicOPDS')
        self.assertEqual(ctx.exception.status_code, 422)

    def test_other_hosts_are_not_added_to_allowlist(self):
        with patch.object(im.socket, 'getaddrinfo') as dns:
            with self.assertRaises(im.HTTPException) as ctx:
                im._public_remote('https://my-nas.local/admin')
        self.assertEqual(ctx.exception.status_code, 400)
        dns.assert_not_called()

    def test_approved_host_must_still_resolve_to_public_ip(self):
        with patch.object(im.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaises(im.HTTPException) as ctx:
                im._public_remote(self.REPO)
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == '__main__':
    unittest.main()
