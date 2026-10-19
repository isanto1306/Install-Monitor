# SPDX-License-Identifier: GPL-3.0-only
"""Offline regression coverage for pinned Codeberg + Git LFS builds."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

os.environ.setdefault('IM_ADMIN_PASSWORD', 'only-an-offline-test-password')
os.environ.setdefault('IM_SESSION_SECRET', 'offline-tests-do-not-use-this-key-in-production')

import main as im  # noqa: E402


class CodebergBuildTests(unittest.TestCase):
    REPO = 'https://codeberg.org/irelephant/kittygram'
    BRANCH_RAW = REPO + '/raw/branch/main/compose.yaml'
    REVISION = 'a' * 40
    YAML = 'services:\n  kittygram:\n    image: kittygram:latest\n    build: .\n'

    def document(self):
        return {'name': 'kittygram',
                'services': {
                    'kittygram': {'image': 'kittygram:latest',
                                  'build': {'context': '.', 'dockerfile': 'Dockerfile'},
                                  'ports': ['8080:80']},
                    'redis': {'image': 'valkey/valkey:latest'}}}

    def mock_remote(self, url, max_bytes=524288):
        if url.endswith('/commits/main'):
            return '{"sha":"' + self.REVISION + '"}'
        if url == self.REPO + '/raw/commit/' + self.REVISION + '/compose.yaml':
            return self.YAML
        raise AssertionError('Unexpected remote: ' + url)

    def test_codeberg_build_metadata_local_image_and_sanitized_compose(self):
        with patch.object(im, '_download_remote', side_effect=self.mock_remote):
            document, notes = im._attach_codeberg_build_context(
                self.document(), self.REPO, self.BRANCH_RAW, self.YAML)
        self.assertIn('Codeberg', ' '.join(notes))
        spec = im._validated_builds(document)[0]
        self.assertEqual(spec['provider'], 'codeberg')
        self.assertEqual(spec['branch'], 'main')
        self.assertEqual(spec['revision'], self.REVISION)
        self.assertEqual(spec['context'], '.')
        self.assertEqual(spec['image'], 'installmonitor-local/kittygram-kittygram:aaaaaaaaaaaa')
        self.assertEqual(document['services']['redis']['image'], 'valkey/valkey:latest')
        yaml_out = im._zimaos_compose(document)
        self.assertNotIn('x-install-monitor-codeberg', yaml_out)
        self.assertNotIn('build:', yaml_out)

    def test_reviewed_compose_must_match_pinned_commit(self):
        def changed_remote(url, max_bytes=524288):
            if url.endswith('/commits/main'):
                return '{"sha":"' + self.REVISION + '"}'
            return 'services: {}'
        with patch.object(im, '_download_remote', side_effect=changed_remote):
            with self.assertRaises(im.HTTPException) as ctx:
                im._attach_codeberg_build_context(
                    self.document(), self.REPO, self.BRANCH_RAW, self.YAML)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_unpinned_and_forged_build_metadata_rejected(self):
        doc = self.document()
        doc['services']['kittygram']['image'] = 'installmonitor-local/kittygram-kittygram:aaaaaaaaaaaa'
        doc['x-install-monitor-codeberg'] = {'repository': 'https://evil.example/kittygram',
                                             'revision': self.REVISION, 'branch': 'main',
                                             'compose_dir': '.'}
        with self.assertRaises(im.HTTPException):
            im._validated_builds(doc)

    def mock_git(self, actions, current=None, oversized=False):
        def execute(cmd, **kwargs):
            if 'clone' in cmd:
                path = Path(cmd[-1])
                path.mkdir(parents=True, exist_ok=True)
                (path / '.git').mkdir()
                (path / 'assets').mkdir()
                size = 300 * 1024 * 1024 if oversized else 16
                (path / 'assets' / 'data.bin').write_text(
                    'version https://git-lfs.github.com/spec/v1\n'
                    + 'oid sha256:' + ('0' * 64) + '\n'
                    + 'size ' + str(size) + '\n')
                actions.append('clone')
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            if 'rev-parse' in cmd:
                actions.append('rev-parse')
                return SimpleNamespace(returncode=0, stdout=current or self.REVISION, stderr='')
            if 'ls-files' in cmd:
                actions.append('lfs-ls')
                return SimpleNamespace(returncode=0, stdout='assets/data.bin\n', stderr='')
            if 'pull' in cmd:
                actions.append('lfs-pull')
                if not oversized:
                    path = Path(cmd[cmd.index('-C') + 1])
                    (path / 'assets' / 'data.bin').write_bytes(b'FILE_CONTENT_FROM_LFS')
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            if 'checkout' in cmd:
                actions.append('checkout')
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            raise AssertionError(str(cmd))
        return execute

    def test_lfs_pointer_is_fetched_after_commit_verified(self):
        actions = []
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(im.subprocess, 'run', side_effect=self.mock_git(actions)):
                result = im._archive_codeberg_tree(self.REPO, 'main', self.REVISION,
                                                   Path(tmp) / 'source')
            self.assertTrue((result / 'assets' / 'data.bin').is_file())
        self.assertEqual(actions, ['clone', 'rev-parse', 'checkout', 'lfs-ls', 'lfs-pull'])

    def test_changed_branch_refused_before_checkout(self):
        actions = []
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(im.subprocess, 'run',
                              side_effect=self.mock_git(actions, current='b' * 40)):
                with self.assertRaises(im.HTTPException) as ctx:
                    im._archive_codeberg_tree(self.REPO, 'main', self.REVISION,
                                               Path(tmp) / 'source')
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(actions, ['clone', 'rev-parse'])

    def test_symlink_in_source_rejected(self):
        actions = []

        def with_symlink(cmd, **kwargs):
            result = self.mock_git(actions)(cmd, **kwargs)
            if 'checkout' in cmd:
                source = Path(cmd[cmd.index('-C') + 1])
                (source / 'unsafe-link').symlink_to('/etc/passwd')
            return result

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(im.subprocess, 'run', side_effect=with_symlink):
                with self.assertRaises(im.HTTPException) as ctx:
                    im._archive_codeberg_tree(self.REPO, 'main', self.REVISION,
                                               Path(tmp) / 'source')
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertNotIn('lfs-pull', actions)

    def test_oversized_lfs_refused_before_download(self):
        actions = []
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(im.subprocess, 'run',
                              side_effect=self.mock_git(actions, oversized=True)):
                with self.assertRaises(im.HTTPException) as ctx:
                    im._archive_codeberg_tree(self.REPO, 'main', self.REVISION,
                                               Path(tmp) / 'source')
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertNotIn('lfs-pull', actions)


if __name__ == '__main__':
    unittest.main()
