# SPDX-License-Identifier: GPL-3.0-only
"""Headplane config wizard: explicit endpoints, exclusive app-owned file."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-use-on-nas')
import main as im  # noqa: E402

EXAMPLE = """
name: headplane
services:
  headplane:
    image: ghcr.io/tale/headplane:latest
    volumes:
      - /DATA/AppData/headplane/config.yaml:/etc/headplane/config.yaml
      - /DATA/AppData/headplane/data:/var/lib/headplane
"""

class HeadplaneConfigWizardTests(unittest.TestCase):
    def test_required_bind_and_publisher_identity(self):
        self.assertEqual(im._im_headplane_config_service(im.safe_yaml(EXAMPLE)),
                         ('headplane', '/DATA/AppData/headplane/config.yaml'))
        for source in [
            EXAMPLE.replace('/DATA/AppData/headplane/config.yaml',
                            './config.yaml'),
            EXAMPLE.replace('ghcr.io/tale/headplane:latest', 'other/image:latest'),
            EXAMPLE.replace('name: headplane', 'name: anotherapp'),
        ]:
            with self.assertRaises(im.HTTPException):
                im._im_headplane_config_service(im.safe_yaml(source))

    def test_urls_are_explicit_and_without_secret_leaks(self):
        for bad in ('', 'localhost:8080', 'http://localhost:8080',
                    'http://127.0.0.1:8080', 'http://0.0.0.0:3001',
                    'ftp://example.org', 'http://user:pw@example.org',
                    'https://example.org/admin', 'http://server:bad',
                    'http://server:8080?key=x'):
            with self.subTest(bad=bad), self.assertRaises(im.HTTPException):
                im._im_headplane_url(bad, 'Test')
        self.assertEqual(im._im_headplane_url(
            'http://headscale:8080/', 'Headscale'), 'http://headscale:8080')
        self.assertEqual(im._im_headplane_url(
            'https://my-server.example.org', 'Headplane'),
            'https://my-server.example.org')

    def test_preview_missing_file_stays_blocked(self):
        with patch.object(im, '_im_host_file_mount_issues',
                          return_value=['headplane: Datei-Mount /DATA/AppData/headplane/config.yaml existiert nicht.']), \
             patch.object(im, 'require_ports_free',
                          return_value={'ports': [], 'blocked': False}), \
             patch.object(im, '_im_external_network_issues', return_value=[]):
            result = im.build_plan(im.Plan(
                source=EXAMPLE, name='headplane', title='Headplane'))
        self.assertFalse(result['install_ready'])
        self.assertTrue(any('config.yaml' in issue for issue in result['setup_issues']))

    def test_explicit_user_urls_generate_random_secret_through_stdin_only(self):
        invocations = []
        def fake_run(cmd, **kw):
            invocations.append((cmd,kw))
            if cmd[1] == 'inspect':
                return SimpleNamespace(stdout='sha256:'+'a'*64+'\n')
            return SimpleNamespace(stdout=json.dumps({
                'created':True, 'path':'/DATA/AppData/headplane/config.yaml'
            }))
        with patch.object(im, 'require_write'), \
             patch.object(im.subprocess, 'run', side_effect=fake_run):
            result = im.create_headplane_config(None, im.HeadplaneConfigSetup(
                compose=EXAMPLE, headscale_url='http://headscale.example.test:8080',
                base_url='http://nas.example.test:3001'))
        self.assertEqual(result, {'created':True,
                                  'path':'/DATA/AppData/headplane/config.yaml'})
        self.assertEqual(len(invocations),2)
        cmd,kwargs=invocations[1]
        self.assertIn('--network',cmd)
        self.assertIn('none',cmd)
        self.assertIn('--read-only',cmd)
        self.assertIn('--mount',cmd)
        self.assertIn('--pids-limit',cmd)
        self.assertIn('-i',cmd)
        data=json.loads(kwargs['input'])
        config=yaml.safe_load(data['content'])
        self.assertEqual(config['headscale']['url'], 'http://headscale.example.test:8080')
        self.assertEqual(config['server']['base_url'], 'http://nas.example.test:3001')
        self.assertFalse(config['server']['cookie_secure'])
        self.assertEqual(len(config['server']['cookie_secret']),32)
        self.assertEqual(config['server']['data_path'], '/var/lib/headplane')
        self.assertNotIn(config['server']['cookie_secret'],str(cmd))
        self.assertNotIn(config['server']['cookie_secret'],str(result))
        self.assertFalse(any(k.startswith('IM_PREPARE') for k in cmd))

    def test_writer_creates_file_only_once_no_overwrite_or_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            writer=im._IM_HEADPLANE_CONFIG_WRITER.replace(
                "Path('/im-appdata')", f"Path({str(root)!r})")
            payload=json.dumps({'app':'headplane',
                                'content':'server:\n  cookie_secret: test\n'})
            def run():
                return subprocess.run([sys.executable,'-c',writer],
                                      input=payload,text=True,capture_output=True)
            first=run()
            self.assertEqual(first.returncode,0,first.stderr)
            path=root/'headplane'/'config.yaml'
            self.assertTrue(path.is_file())
            self.assertIn('cookie_secret: test',path.read_text())
            second=run()
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(path.read_text(),'server:\n  cookie_secret: test\n')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'headplane').symlink_to(root, target_is_directory=True)
            writer=im._IM_HEADPLANE_CONFIG_WRITER.replace(
                "Path('/im-appdata')", f"Path({str(root)!r})")
            third=subprocess.run([sys.executable,'-c',writer],
                                 input=payload,text=True,capture_output=True)
            self.assertNotEqual(third.returncode,0)
            self.assertFalse((root/'config.yaml').exists())

    def test_refuses_headscale_url_with_embedded_credentials(self):
        with patch.object(im, 'require_write'), \
             patch.object(im.subprocess,'run') as run:
            with self.assertRaises(im.HTTPException):
                im.create_headplane_config(None,im.HeadplaneConfigSetup(
                    compose=EXAMPLE,headscale_url='http://admin:token@headscale:8080',
                    base_url='http://nas.local:3001'))
        run.assert_not_called()

if __name__=='__main__':
    unittest.main()
