# SPDX-License-Identifier: GPL-3.0-only
"""Beta 14 offline regressions for automatic Compose preparation."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("IM_ADMIN_PASSWORD", "test-password-only")
os.environ.setdefault("IM_SESSION_SECRET", "test-session-secret-not-for-use-on-nas")

import yaml  # noqa: E402
import main as im  # noqa: E402


class Beta14ComposeAutomationTests(unittest.TestCase):
    def test_local_postgres_consistent_user_database_and_password(self):
        source = """
name: example
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
  app:
    image: example/app:latest
    environment:
      DATABASE_USERNAME: ${POSTGRES_USER}
      DATABASE_PASSWORD: ${POSTGRES_PASSWORD}
      DATABASE_NAME: ${POSTGRES_DB}
"""
        resolved, notes = im._resolve_compose_variables(source)
        doc = yaml.safe_load(resolved)
        db = doc["services"]["db"]["environment"]
        app = doc["services"]["app"]["environment"]
        self.assertTrue(db["POSTGRES_USER"].startswith("app_"))
        self.assertEqual(db["POSTGRES_DB"], "appdb")
        self.assertGreaterEqual(len(db["POSTGRES_PASSWORD"]), 20)
        self.assertEqual(app["DATABASE_USERNAME"], db["POSTGRES_USER"])
        self.assertEqual(app["DATABASE_PASSWORD"], db["POSTGRES_PASSWORD"])
        self.assertEqual(app["DATABASE_NAME"], db["POSTGRES_DB"])
        self.assertFalse(im._unresolved_runtime_variables(doc))
        again, _ = im._resolve_compose_variables(resolved)
        self.assertEqual(yaml.safe_load(again), doc)
        self.assertTrue(any("POSTGRES_PASSWORD" in n for n in notes))

    def test_explicit_upstream_value_is_preferred(self):
        source = """
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: original_owner
  app:
    image: example/app:latest
    environment:
      DB_USERNAME: ${POSTGRES_USER}
"""
        resolved, _ = im._resolve_compose_variables(source)
        doc = yaml.safe_load(resolved)
        self.assertEqual(doc["services"]["app"]["environment"]["DB_USERNAME"], "original_owner")

    def test_external_token_or_unknown_host_value_not_fabricated(self):
        source = """
services:
  app:
    image: example/app:latest
    environment:
      API_TOKEN: ${API_TOKEN}
      CUSTOM_NAS_PATH: ${CUSTOM_NAS_PATH}
"""
        resolved, _ = im._resolve_compose_variables(source)
        doc = yaml.safe_load(resolved)
        self.assertEqual(im._unresolved_runtime_variables(doc), {
            "${API_TOKEN}", "${CUSTOM_NAS_PATH}"})

    def test_unrelated_user_is_not_generated_without_local_db(self):
        source = """
services:
  app:
    image: example/app:latest
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
"""
        resolved, _ = im._resolve_compose_variables(source)
        self.assertIn("${POSTGRES_USER}", resolved)

    @patch.object(im, "_host_timezone", return_value=("Europe/Paris", ""))
    def test_timezone_placeholder_uses_detected_host(self, _probe):
        source = """
services:
  app:
    image: example/app:latest
    environment:
      TZ: ${TZ}
"""
        resolved, _ = im._resolve_compose_variables(source)
        self.assertEqual(yaml.safe_load(resolved)["services"]["app"]["environment"]["TZ"],
                         "Europe/Paris")

    @patch.object(im, "_host_timezone", return_value=("", "not available"))
    def test_missing_timezone_does_not_install_arbitrary_region(self, _probe):
        source = """
services:
  app:
    image: example/app:latest
    environment:
      TZ: America/Toronto
"""
        doc = yaml.safe_load(source)
        plan = im.Plan(source=source, name="example", title="Example")
        notes = []
        im._apply_timezone_choice(doc, plan, notes)
        self.assertEqual(doc["services"]["app"]["environment"]["TZ"], "America/Toronto")
        self.assertTrue(any("nicht ermittelbar" in message for message in notes))

    def test_full_docker_error_visible_but_secret_hidden(self):
        password = "topsecretPASSWORDvalue"
        doc = {"services": {"app": {"environment": {"DB_PASSWORD": password}}}}
        error = ("failed to create task for container: OCI runtime create failed: "
                 "runc create failed: unable to apply apparmor profile: "
                 "open /proc/thread-self/attr/apparmor/exec: read-only file system "
                 + password)
        safe = im._im_safe_runtime_error(error, doc)
        self.assertIn("read-only file system", safe)
        self.assertIn("apparmor", safe)
        self.assertNotIn(password, safe)
        self.assertIn("[REDACTED]", safe)


if __name__ == "__main__":
    unittest.main()
