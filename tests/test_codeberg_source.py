# SPDX-License-Identifier: GPL-3.0-only
"""Regression coverage for Codeberg/Forgejo project and Compose-file URLs."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'unit-test-session-secret-only-not-production')

import main as im  # noqa: E402


class CodebergSourceTests(unittest.TestCase):
    REPO = 'https://codeberg.org/irelephant/kittygram'
    COMPOSE = """services:
  kittygram:
    build: .
    ports:
      - "3000:3000"
  valkey:
    image: valkey/valkey:8-alpine
"""

    def test_codeberg_project_discovers_root_compose(self):
        seen = []

        def fake_download(url, max_bytes=524288):
            seen.append(url)
            if url.endswith('/api/v1/repos/irelephant/kittygram'):
                return '{"default_branch": "main"}'
            if '/git/trees/' in url:
                return '{"tree":[{"type":"blob","path":"compose.yaml"}]}'
            if url.endswith('/raw/branch/main/compose.yaml'):
                return self.COMPOSE
            raise im.HTTPException(404, 'Nicht gefunden')

        with patch.object(im, '_download_remote', side_effect=fake_download), \
                patch.object(im, '_public_remote', side_effect=lambda url: url):
            source, resolved, notes = im.discover_source(self.REPO)
        self.assertEqual(source, self.COMPOSE)
        self.assertEqual(resolved, self.REPO + '/raw/branch/main/compose.yaml')
        self.assertTrue(any('Codeberg' in note for note in notes))
        self.assertTrue(any('Build-Kontext' in note for note in notes))
        self.assertTrue(any('/compose.yaml' in url for url in seen))

    def test_codeberg_file_page_converts_to_raw(self):
        file_url = self.REPO + '/src/branch/main/compose.yaml'
        with patch.object(im, '_public_remote', side_effect=lambda url: url), \
                patch.object(im, '_download_remote', return_value=self.COMPOSE) as download:
            source, resolved, notes = im.discover_source(file_url)
        self.assertEqual(source, self.COMPOSE)
        self.assertEqual(resolved, self.REPO + '/raw/branch/main/compose.yaml')
        download.assert_called_once_with(resolved)
        self.assertEqual(notes, [])

    def test_missing_compose_is_explained(self):
        def fake_download(url, max_bytes=524288):
            if url.endswith('/api/v1/repos/irelephant/kittygram'):
                return '{"default_branch":"main"}'
            if '/git/trees/' in url:
                return '{"tree":[]}'
            raise im.HTTPException(404, 'Nicht gefunden')

        with patch.object(im, '_public_remote', side_effect=lambda url: url), \
                patch.object(im, '_download_remote', side_effect=fake_download):
            with self.assertRaises(im.HTTPException) as ctx:
                im.discover_source(self.REPO)
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn('Codeberg', str(ctx.exception.detail))

    def test_invalid_codeberg_file_path_is_rejected(self):
        with patch.object(im, '_public_remote', side_effect=lambda url: url):
            with self.assertRaises(im.HTTPException) as ctx:
                im.discover_source(self.REPO + '/src/branch/main/README.md')
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == '__main__':
    unittest.main()
