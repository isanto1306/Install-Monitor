# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests for the official HealthLog Compose secret fields."""
import os
import re
import unittest

os.environ.setdefault("IM_ADMIN_PASSWORD", "test-password-only")
os.environ.setdefault("IM_SESSION_SECRET", "test-session-secret-not-for-use-on-nas")

import yaml  # noqa: E402
import main as im  # noqa: E402


class HealthLogSecretTests(unittest.TestCase):
    TEMPLATE = """
name: healthlog
x-healthlog-env: &healthlog_env
  API_TOKEN_HMAC_KEY: ${API_TOKEN_HMAC_KEY}
  ENCRYPTION_KEY: ${ENCRYPTION_KEY}
services:
  app:
    image: ghcr.io/mbombeck/healthlog${HEALTHLOG_IMAGE_REF:-:latest}
    environment:
      <<: *healthlog_env
  app-worker:
    image: ghcr.io/mbombeck/healthlog:latest
    environment:
      <<: *healthlog_env
"""

    def test_required_hmac_is_generated_and_shared(self):
        result, notes = im._resolve_compose_variables(self.TEMPLATE)
        doc = yaml.safe_load(result)
        app = doc["services"]["app"]["environment"]
        worker = doc["services"]["app-worker"]["environment"]
        hmac_key = app["API_TOKEN_HMAC_KEY"]
        self.assertRegex(hmac_key, r"^[a-f0-9]{64}$")
        self.assertEqual(worker["API_TOKEN_HMAC_KEY"], hmac_key)
        self.assertRegex(app["ENCRYPTION_KEY"], r"^[a-f0-9]{64}$")
        self.assertNotEqual(app["ENCRYPTION_KEY"], hmac_key)
        self.assertEqual(im._unresolved_runtime_variables(doc), set())
        self.assertTrue(any("API_TOKEN_HMAC_KEY" in line for line in notes))

    def test_resolved_key_not_rotated_on_later_pass(self):
        resolved, _ = im._resolve_compose_variables(self.TEMPLATE)
        again, _ = im._resolve_compose_variables(resolved)
        a = yaml.safe_load(resolved)["services"]["app"]["environment"]
        b = yaml.safe_load(again)["services"]["app"]["environment"]
        self.assertEqual(a["API_TOKEN_HMAC_KEY"], b["API_TOKEN_HMAC_KEY"])

    def test_unknown_api_hmac_placeholder_is_not_assumed_local(self):
        source = """
services:
  app:
    image: another-vendor/unknown:latest
    environment:
      API_TOKEN_HMAC_KEY: ${API_TOKEN_HMAC_KEY}
"""
        rendered, _ = im._resolve_compose_variables(source)
        self.assertIn("${API_TOKEN_HMAC_KEY}", rendered)


if __name__ == "__main__":
    unittest.main()
