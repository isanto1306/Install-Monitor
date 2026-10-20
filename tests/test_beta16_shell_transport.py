# SPDX-License-Identifier: GPL-3.0-only
"""Beta 16: POSIX shell commands survive one or multiple Compose passes."""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

os.environ.setdefault('IM_ADMIN_PASSWORD', 'test-password-only')
os.environ.setdefault('IM_SESSION_SECRET', 'test-session-secret-not-for-use-on-nas')
import main as im  # noqa: E402


class Beta16SafeShellTransportTests(unittest.TestCase):
    def _transport(self, script: str, *, entrypoint=False):
        if entrypoint:
            svc = {'image': 'alpine:3.20',
                   'entrypoint': ['/bin/sh', '-c'], 'command': [script]}
        else:
            svc = {'image': 'alpine:3.20',
                   'command': ['/bin/sh', '-c', script]}
        doc = {'services': {'nametag-init': svc}}
        exported = yaml.safe_load(im._zimaos_compose(doc))
        self.assertEqual(doc['services']['nametag-init']['command'][-1], script,
                         'The wizard document must never mutate')
        return exported['services']['nametag-init']['command'][-1]

    def _run_stub(self, stub: str, env=None):
        # Execute with the same POSIX /bin/sh interpreter as Nametag's Alpine.
        # No container engine, NAS path or network is involved.
        return subprocess.run(['/bin/sh', '-c', stub], env=env, text=True,
                              capture_output=True, timeout=8, check=False)

    def test_nametag_init_file_target_survives_multi_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_file = Path(directory) / 'secrets.env'
            script = f"""set -e
secrets={secret_file}
rand() {{ printf 'some-random-value'; }}
db=$$(rand 24)
umask 077
printf 'DB_PASSWORD=%s\n' "$$db" > "$$secrets"
. "$$secrets"
printf '%s\n' "$$DB_PASSWORD"
"""
            stub = self._transport(script)
            self.assertNotIn('$', stub, 'No Compose-expansible tokens on the wire')
            self.assertNotIn('secrets.env', stub, 'Publisher script stays encoded')
            result = self._run_stub(stub)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'some-random-value')
            self.assertEqual(secret_file.read_text(), 'DB_PASSWORD=some-random-value\n')
            self.assertEqual(secret_file.stat().st_mode & 0o777, 0o600)

    def test_cron_environment_references_remain_shell_runtime_values(self):
        script = """auth="Authorization: Bearer $$CRON_SECRET"
job() { printf '%s:%s\n' "$$1" "$$auth"; }
job test
"""
        stub = self._transport(script)
        result = self._run_stub(stub, env={**os.environ, 'CRON_SECRET':'test-only-token'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('test:Authorization: Bearer test-only-token', result.stdout)

    def test_entrypoint_form_supports_script_as_command(self):
        script = "value=test\nprintf '%s\n' \"$$value\""
        stub = self._transport(script, entrypoint=True)
        self.assertEqual(self._run_stub(stub).stdout.strip(), 'test')

    def test_regular_shell_command_without_compose_escape_is_untouched(self):
        original = ['/bin/sh', '-c', 'echo plain text']
        doc = {'services': {'service': {'image': 'alpine:3.20', 'command': original}}}
        result = yaml.safe_load(im._zimaos_compose(doc))
        self.assertEqual(result['services']['service']['command'], original)

    def test_non_shell_command_is_not_rewritten(self):
        original = ['node', 'server.js', '$$something']
        doc = {'services': {'service': {'image': 'node:22', 'command': original}}}
        result = yaml.safe_load(im._zimaos_compose(doc))
        self.assertEqual(result['services']['service']['command'], original)

    def test_large_shell_script_fails_closed(self):
        script = "echo '$$VALUE'\n" + "x" * 16001
        with self.assertRaises(im.HTTPException) as ctx:
            self._transport(script)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn('zu lang', str(ctx.exception.detail))

    def test_pass_through_two_simulated_compose_evaluations(self):
        script = "value=/data/secrets.env\nprintf 'ok' > \"$$value\""
        stub = self._transport(script)
        for _ in range(2):
            stub = stub.replace('$$', '$')
            stub = re.sub(r'\$[A-Za-z_][A-Za-z0-9_]*', '', stub)
        self.assertNotIn('$', stub)
        # /tmp is used only in isolated tests above; here the literal script
        # reconstruction proves the runtime target is still a variable.
        self.assertEqual(stub, self._transport(script))


if __name__ == '__main__':
    unittest.main()
