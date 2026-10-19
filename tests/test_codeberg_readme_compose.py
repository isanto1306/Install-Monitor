# SPDX-License-Identifier: GPL-3.0-only
"""Offline tests: a Codeberg README can document an image-backed Compose."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-only-secret-credential')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-production')

import main as im  # noqa: E402


class CodebergReadmeComposeTests(unittest.TestCase):
    README = """# RSS
A simple RSS reader.

No authentication or authorization built-in.

### Docker Compose Example
```yml
version: "2"
services:
  rss:
    image: codeberg.org/danb/rss:latest
    environment:
      - APP_NAME=RSS
    volumes:
      - ./rss-files:/app/storage
    ports:
      - "8080:80"
    restart: unless-stopped
```

Other text.
"""

    def fetch(self, url, max_bytes=524288):
        if url.endswith('/api/v1/repos/danb/rss'):
            return '{"default_branch":"main"}'
        if '/git/trees/' in url:
            return '{"tree":[{"type":"blob","path":"README.md"},'
                   '{"type":"blob","path":"Dockerfile"}]}'
        if url.endswith('/raw/branch/main/README.md'):
            return self.README
        raise im.HTTPException(404, 'No separate Compose in repository')

    def test_readme_compose_is_used_after_missing_root_files(self):
        with patch.object(im, '_download_remote', side_effect=self.fetch):
            rendered, source_url, notes = im._discover_codeberg_project('danb', 'rss')
        doc = im.safe_yaml(rendered)
        self.assertEqual(source_url, 'https://codeberg.org/danb/rss/raw/branch/main/README.md')
        self.assertEqual(doc['services']['rss']['image'], 'codeberg.org/danb/rss:latest')
        self.assertEqual(doc['services']['rss']['ports'], ['8080:80'])
        self.assertTrue(doc[im._DOC_IMAGE_PREFLIGHT])
        self.assertTrue(any('Authentifizierung' in item for item in notes))
        self.assertTrue(any('Registry-Manifest' in item for item in notes))

    def test_an_unrelated_compose_example_must_not_be_installed(self):
        foreign = self.README.replace('codeberg.org/danb/rss:latest', 'evil.example/foreign:latest')
        with patch.object(im, '_download_remote', return_value=foreign):
            self.assertIsNone(im._codeberg_readme_compose('danb', 'rss', 'main'))

    def test_incomplete_yaml_example_is_ignored(self):
        partial = 'Docker example:\n'+ '```yaml\nservices:\n  rss:\n    image: codeberg.org/danb/rss:latest\n  db:\n    environment:\n      - FOO=bar\n```\n'
        with patch.object(im, '_download_remote', return_value=partial):
            self.assertIsNone(im._codeberg_readme_compose('danb', 'rss', 'main'))

    def test_root_compose_has_precedence_over_readme(self):
        root = 'services:\n  rss:\n    image: codeberg.org/danb/rss:latest\n'
        def fetch(url, max_bytes=524288):
            if url.endswith('/api/v1/repos/danb/rss'):
                return '{"default_branch":"main"}'
            if '/git/trees/' in url:
                return '{"tree":[{"type":"blob","path":"compose.yaml"}]}'
            if url.endswith('/raw/branch/main/compose.yaml'):
                return root
            raise im.HTTPException(404, 'not found')
        with patch.object(im, '_download_remote', side_effect=fetch):
            body, url, notes = im._discover_codeberg_project('danb', 'rss')
        self.assertEqual(body, root)
        self.assertEqual(url, 'https://codeberg.org/danb/rss/raw/branch/main/compose.yaml')
        self.assertFalse(any('README' in item for item in notes))


if __name__ == '__main__':
    unittest.main()
