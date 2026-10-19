# SPDX-License-Identifier: GPL-3.0-only
"""Codeberg commit resolution must fail closed and support Git HTTPS fallback."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-only-value')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-production')

import main as im  # noqa: E402


class CommitResolverTests(unittest.TestCase):
    REPO = 'https://codeberg.org/irelephant/kittygram'
    SHA = 'a' * 40

    def test_commit_api_first(self):
        with patch.object(im, '_download_remote',
                          return_value='{"sha":"' + self.SHA + '"}') as remote, \
             patch.object(im.subprocess, 'run') as git:
            self.assertEqual(im._codeberg_branch_revision(self.REPO, 'main'), self.SHA)
        remote.assert_called_once()
        git.assert_not_called()

    def test_forgejo_branch_api_if_commit_endpoint_unavailable(self):
        def download(url, max_bytes=524288):
            if '/commits/main' in url:
                raise im.HTTPException(403, 'upstream blocked')
            if '/branches/main' in url:
                return '{"commit":{"id":"' + self.SHA + '"}}'
            raise AssertionError(url)

        with patch.object(im, '_download_remote', side_effect=download), \
             patch.object(im.subprocess, 'run') as git:
            self.assertEqual(im._codeberg_branch_revision(self.REPO, 'main'), self.SHA)
        git.assert_not_called()

    def test_https_git_fallback_when_both_api_routes_fail(self):
        ref = 'refs/heads/main'
        fake = SimpleNamespace(returncode=0, stdout=self.SHA + '\t' + ref + '\n',
                               stderr='')
        with patch.object(im, '_download_remote',
                          side_effect=im.HTTPException(403, 'API forbidden')), \
             patch.object(im.subprocess, 'run', return_value=fake) as git:
            self.assertEqual(im._codeberg_branch_revision(self.REPO, 'main'), self.SHA)
        args, kwargs = git.call_args
        self.assertIn('ls-remote', args[0])
        self.assertIn('--exit-code', args[0])
        self.assertIn('https://codeberg.org/irelephant/kittygram.git', args[0])
        self.assertIn(ref, args[0])
        self.assertEqual(kwargs['env']['GIT_TERMINAL_PROMPT'], '0')
        self.assertFalse(kwargs['check'])

    def test_wrong_ref_does_not_count_as_verified(self):
        fake = SimpleNamespace(returncode=0,
                               stdout=self.SHA + '\trefs/heads/unrelated\n', stderr='')
        with patch.object(im, '_download_remote',
                          side_effect=im.HTTPException(404, 'missing')), \
             patch.object(im.subprocess, 'run', return_value=fake):
            with self.assertRaises(im.HTTPException) as failure:
                im._codeberg_branch_revision(self.REPO, 'main')
        self.assertEqual(failure.exception.status_code, 503)

    def test_both_unavailable_must_block_build(self):
        fake = SimpleNamespace(returncode=128, stdout='', stderr='credential secret')
        with patch.object(im, '_download_remote',
                          side_effect=im.HTTPException(403, 'missing')), \
             patch.object(im.subprocess, 'run', return_value=fake):
            with self.assertRaises(im.HTTPException) as failure:
                im._codeberg_branch_revision(self.REPO, 'main')
        self.assertEqual(failure.exception.status_code, 503)
        self.assertNotIn('credential secret', failure.exception.detail)

    def test_reject_invalid_branch_before_network(self):
        with patch.object(im, '_download_remote') as remote, \
             patch.object(im.subprocess, 'run') as git:
            with self.assertRaises(im.HTTPException) as failure:
                im._codeberg_branch_revision(self.REPO, '../malicious')
        self.assertEqual(failure.exception.status_code, 400)
        remote.assert_not_called()
        git.assert_not_called()


if __name__ == '__main__':
    unittest.main()
