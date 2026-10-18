# SPDX-License-Identifier: GPL-3.0-only
"""Non-invasive offline checks. No Docker daemon or NAS writes are performed."""
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from setup_credentials import write_configuration

class PublicReleaseTests(unittest.TestCase):
    def test_compose_version_network_and_private_registry(self):
        doc=yaml.safe_load((ROOT/'docker-compose.yml').read_text(encoding='utf-8'))
        app=doc['services']['install-monitor']
        registry=doc['services']['registry']
        self.assertEqual(doc['x-casaos']['version'],'0.2.56')
        self.assertEqual(app['image'],'install-monitor:0.2.56-local')
        self.assertEqual(app['env_file'], ['/DATA/AppData/Install-Monitor/.env'])
        self.assertEqual(app['network_mode'],'host')
        self.assertIn('127.0.0.1:50813:5000',registry['ports'])
        self.assertTrue(any('/var/run/docker.sock:' in v for v in app['volumes']))
    def test_secure_credentials_script(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'.env'
            write_configuration(p, 'nas-admin','TestPassphrase123!','abc'*20)
            content=p.read_text()
            self.assertIn('IM_ADMIN_USERNAME=nas-admin',content)
            self.assertIn('pbkdf2_sha256:',content)
            self.assertNotIn('TestPassphrase123!',content)
            self.assertIn('IM_SESSION_SECRET=',content)
            self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            with self.assertRaises(FileExistsError):
                write_configuration(p, 'nas-admin','TestPassphrase123!','abc'*20)
    def _fake_docker_env(self,d):
        bin_dir=Path(d)/'bin';bin_dir.mkdir()
        script=bin_dir/'docker'
        script.write_text('''#!/bin/sh
case "$1 $2 $3" in
 "container inspect "*) exit "${MOCK_INSPECT:-1}" ;;
 "exec "*) exit 0 ;;
esac
exit 0
''')
        script.chmod(0o755)
        env={**os.environ,'PATH':str(bin_dir)+os.pathsep+os.environ['PATH']}
        return env
    def test_read_only_check_mode(self):
        with tempfile.TemporaryDirectory() as d:
            env=self._fake_docker_env(d)
            p=subprocess.run(['sh',str(ROOT/'install.sh'),'--check'],env=env,text=True,capture_output=True,timeout=8)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('Keine Dateien erzeugt',p.stdout)
    def test_existing_installation_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            env=self._fake_docker_env(d)
            env['MOCK_INSPECT']='0'
            p=subprocess.run(['sh',str(ROOT/'install.sh'),'--docker'],env=env,text=True,capture_output=True,timeout=8)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('existiert bereits',p.stderr)
    def test_non_destructive_mock_first_install(self):
        # Rewrite only test-copy paths; published installer remains unchanged.
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)
            root=tmp/'DATA'/'AppData'
            state=root/'Install-Monitor'
            state.mkdir(parents=True)
            envfile=state/'.env'
            write_configuration(envfile,'sample-admin','PasswordForTest123!', 's'*60)
            env=self._fake_docker_env(d)
            code=(ROOT/'install.sh').read_text(encoding='utf-8')
            code=code.replace('/DATA/AppData/Install-Monitor','__MOCK_STATE__').replace('/DATA/AppData',str(root)).replace('__MOCK_STATE__',str(state))
            # UNIX socket from test, not the NAS.
            sockpath=tmp/'test.sock'
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
                sock.bind(str(sockpath))
                code=code.replace('/var/run/docker.sock',str(sockpath))
                inst=tmp/'installer-mock.sh';inst.write_text(code);inst.chmod(0o755)
                out=subprocess.run(['sh',str(inst),'--docker'],env=env,text=True,capture_output=True,timeout=15)
            # First attempt has no application files in the mock source directory.
            self.assertNotEqual(out.returncode,0)
            self.assertIn('Dateien fehlen',out.stderr)
            # Provide a full project source without using the real Docker daemon.
            for name in ['main.py','static/app.js','static/style.css',
                         'static/index.html','static/isanto1306-apps-logo.png',
                         'Dockerfile','requirements.txt','docker-compose.yml',
                         'setup_credentials.py']:
                target=tmp/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.symlink_to(ROOT/name)
            # Patch the system-socket check to an isolated test UNIX socket.
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
                sockpath.unlink()
                sock.bind(str(sockpath))
                result=subprocess.run(['sh',str(inst),'--docker'],env=env,
                                      text=True,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            self.assertIn('ERFOLG: Install Monitor v0.2.56 läuft',result.stdout)
            self.assertNotIn('PasswordForTest123!',result.stdout+result.stderr)
            self.assertNotIn('ssssssss',result.stdout+result.stderr)
            self.assertTrue((state/'data').is_dir())
            self.assertTrue((state/'registry').is_dir())
    def test_source_has_current_release_version(self):
        script=(ROOT/'install.sh').read_text()
        self.assertIn('v0.2.56',script)
        self.assertNotIn('0.1.22',script)
        self.assertNotIn('register_zimaos.py', script)

if __name__=='__main__':unittest.main()
