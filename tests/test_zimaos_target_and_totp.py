# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests for saving the NAS address and enforcing install 2FA."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("IM_ADMIN_PASSWORD", "unit-test-secret-only")
os.environ.setdefault("IM_SESSION_SECRET", "unit-test-session-secret-not-for-production")

import main as im  # noqa: E402


class ZimaOsInstallSecurityTests(unittest.TestCase):
    def test_target_is_saved_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target.json"
            with (patch.object(im, "_ZIMAOS_TARGET_FILE", path),
                  patch.object(im, "require_write"),
                  patch.object(im, "require_auth"),
                  patch.object(im, "safe_host", return_value="http://192.168.178.191")):
                result = im.save_zimaos_target(SimpleNamespace(), im.ZimaOsTargetSave(host="192.168.178.191"))
                self.assertEqual(result, {"host": "http://192.168.178.191"})
                self.assertEqual(im.get_zimaos_target(SimpleNamespace()), result)
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"host": "http://192.168.178.191"})

    def test_lan_target_does_not_bypass_enabled_totp(self):
        payload = im.Install(compose="services: {}", host="http://192.168.178.191",
                             username="admin", password="not-saved", confirmed=True)
        req = SimpleNamespace(session={"csrf": "test-session"})
        with (patch.object(im, "_totp_saved", return_value="ABCDEFGHIJKLMNOP"),
              patch.object(im, "_proxy_hosts", return_value={"monitor.example.org"}),
              patch.object(im, "_verify_totp", return_value=False) as verify):
            with self.assertRaises(im.HTTPException) as result:
                im._install_target(req, payload)
            self.assertEqual(result.exception.status_code, 403)
            verify.assert_called_once()

    def test_valid_totp_works_with_private_target(self):
        payload = im.Install(compose="services: {}", host="http://192.168.178.191",
                             username="admin", password="not-saved", totp_code="123456")
        req = SimpleNamespace(session={"csrf": "test-session"})
        with (patch.object(im, "_totp_saved", return_value="ABCDEFGHIJKLMNOP"),
              patch.object(im, "_proxy_hosts", return_value={"monitor.example.org"}),
              patch.object(im, "_verify_totp", return_value=True) as verify,
              patch.object(im, "safe_host", return_value="http://192.168.178.191")):
            result = im._install_target(req, payload)
            self.assertEqual(result.host, "http://192.168.178.191")
            verify.assert_called_once()

    def test_no_totp_needed_when_not_enabled_and_no_proxy_allowed(self):
        payload = im.Install(compose="services: {}", host="http://192.168.178.191",
                             username="admin", password="not-saved")
        req = SimpleNamespace(session={"csrf": "test-session"})
        with (patch.object(im, "_totp_saved", return_value=""),
              patch.object(im, "_proxy_hosts", return_value=set()),
              patch.object(im, "_verify_totp") as verify,
              patch.object(im, "safe_host", return_value="http://192.168.178.191")):
            self.assertEqual(im._install_target(req, payload).host, "http://192.168.178.191")
            verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
