# SPDX-License-Identifier: GPL-3.0-only
"""Four-source regression matrix: OCI image, GitHub URL, pasted YAML, LSIO catalog.

All external lookups are mocked; comparison checks only common invariants.
"""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("IM_ADMIN_PASSWORD", "test-password-only")
os.environ.setdefault("IM_SESSION_SECRET", "test-session-secret-not-for-use-on-nas")
import main as im  # noqa: E402


IMAGE = "lscr.io/linuxserver/webtest:latest"
UPSTREAM = """
name: webtest
services:
  webtest:
    image: lscr.io/linuxserver/webtest:latest
    restart: unless-stopped
    environment:
      TZ: Europe/Berlin
    ports: ["3444:3000"]
    volumes:
      - /DATA/AppData/webtest/config:/config
    healthcheck:
      test: [CMD-SHELL, "wget -qO- http://localhost:3000/health || exit 1"]
"""
NO_PORTS = """
name: webtest
services:
  webtest:
    image: lscr.io/linuxserver/webtest:latest
    restart: unless-stopped
    expose: ["3000"]
    healthcheck:
      test: [CMD-SHELL, "wget -qO- http://localhost:3000/health || exit 1"]
"""
SHARED = """
name: webtest
services:
  webtest:
    image: lscr.io/linuxserver/webtest:latest
    ports: ["3444:3000"]
    volumes:
      - shared:/data
      - ./config:/config
  worker:
    image: lscr.io/linuxserver/webtest:latest
    volumes:
      - shared:/data:ro
      - ./config:/config:ro
volumes:
  shared:
"""
SOURCE_URL = "https://github.com/example/webtest/blob/main/compose.yaml"
CREDENTIALS = """
name: webtest
services:
  webtest:
    image: lscr.io/linuxserver/webtest:latest
    environment:
      API_TOKEN: ${API_TOKEN}
    ports: ["3444:3000"]
"""


class FourSourceAuditTests(unittest.TestCase):
    def catalog(self):
        return {"name": "webtest", "category": "Others",
                "config": {"ports": [{"internal": "3000", "external": "3444"}],
                           "volumes": [{"path": "/config"}]}}

    def analyze(self, kind, source=UPSTREAM):
        metadata = (
            source, "https://github.com/example/webtest/blob/main/compose.yaml",
            "https://github.com/example/webtest", ["Hersteller-Compose ausgewählt"],
        )
        patches = [
            patch.object(im, "_dockerhub_publisher_documentation", return_value=None),
            patch.object(im, "_publisher_compose_for_image", return_value=metadata),
            patch.object(im, "discover_source",
                         return_value=(source, SOURCE_URL, ["GitHub Compose geladen"])),
            patch.object(im, "_lsio_images", return_value={"webtest": self.catalog()}),
            patch.object(im, "_project_info", return_value=("", "", [])),
            patch.object(im, "_published_images_in_readme", return_value=[]),
            patch.object(im, "_auto_reassign_conflicting_ports", return_value=[]),
            patch.object(im, "_host_timezone", return_value=("Europe/Berlin", "")),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        value = {"image": IMAGE, "url": SOURCE_URL,
                 "yaml": source, "lsio": "webtest"}[kind]
        return im._analyze_source_payload(im.Source(kind=kind, value=value))

    def test_same_web_port_for_four_sources(self):
        results = {kind: self.analyze(kind) for kind in
                   ("image", "url", "yaml", "lsio")}
        for kind, result in results.items():
            with self.subTest(kind=kind):
                doc = im.safe_yaml(result["source"])
                self.assertEqual(result["automation"]["source_type"], kind)
                self.assertEqual(result["automation"]["service_count"], 1)
                self.assertEqual(doc["services"]["webtest"]["ports"], ["3444:3000"])
                self.assertEqual(doc["services"]["webtest"]["image"], IMAGE)

    def test_missing_web_port_completed_consistently_for_source_recipes(self):
        for kind in ("image", "url", "yaml"):
            with self.subTest(kind=kind):
                result = self.analyze(kind, NO_PORTS)
                doc = im.safe_yaml(result["source"])
                self.assertEqual(doc["services"]["webtest"]["ports"],
                                 ["3000:3000"])
                self.assertTrue(any("Healthcheck" in n for n in result["notes"]))

    def test_explicit_credentials_preserved_and_missing_tokens_not_invented(self):
        for kind in ("image", "url", "yaml"):
            with self.subTest(kind=kind):
                result = self.analyze(kind, CREDENTIALS)
                doc = im.safe_yaml(result["source"])
                env = doc["services"]["webtest"]["environment"]
                self.assertEqual(env["API_TOKEN"], "${API_TOKEN}")
                with patch.object(im, "require_ports_free",
                                  return_value={"ports": [], "blocked": False}), \
                     patch.object(im, "_im_host_file_mount_issues", return_value=[]), \
                     patch.object(im, "_im_external_network_issues", return_value=[]):
                    with self.assertRaises(im.HTTPException) as error:
                        im.build_plan(im.Plan(source=result["source"],
                                              name="webtest", title="Webtest"))
                self.assertIn("offene Compose-Variablen", str(error.exception.detail))

    def test_multiservice_volumes_resolved_same_for_github_and_yaml(self):
        for kind in ("url", "yaml"):
            result = self.analyze(kind, SHARED)
            with self.subTest(kind=kind), \
                 patch.object(im, "_im_existing_docker_volume_names", return_value=set()), \
                 patch.object(im, "require_ports_free", return_value={
                     "ports": [], "blocked": False}), \
                 patch.object(im, "_im_host_file_mount_issues", return_value=[]), \
                 patch.object(im, "_im_external_network_issues", return_value=[]):
                plan = im.build_plan(im.Plan(source=result["source"],
                                             name="webtest", title="Webtest"))
            doc = im.safe_yaml(plan["compose"])
            mains = doc["services"]["webtest"]["volumes"]
            workers = doc["services"]["worker"]["volumes"]
            self.assertEqual(mains[0]["source"], workers[0]["source"])
            self.assertEqual(mains[0]["source"], "/DATA/AppData/webtest/shared")
            self.assertEqual(mains[1], "/DATA/AppData/webtest/config:/config")
            self.assertEqual(workers[1], "/DATA/AppData/webtest/config:/config:ro")

    def test_user_permissions_and_restart_policies_are_not_invented(self):
        monline = """
name: webtest
services:
  webtest:
    image: lscr.io/linuxserver/webtest:latest
    restart: unless-stopped
    ports: ["3444:3000"]
    environment:
      PUID: "1000"
      PGID: "1000"
"""
        for kind in ("image", "url", "yaml"):
            with self.subTest(kind=kind):
                result = self.analyze(kind, monline)
                svc = im.safe_yaml(result["source"])["services"]["webtest"]
                self.assertEqual(svc["environment"]["PUID"], "1000")
                self.assertEqual(svc["environment"]["PGID"], "1000")
                self.assertEqual(svc["restart"], "unless-stopped")
                self.assertNotIn("user", svc)
                self.assertNotIn("privileged", svc)
                self.assertNotIn("cap_add", svc)

    def test_source_specific_scoping_is_intentional(self):
        for kind in ("image", "url", "yaml", "lsio"):
            result = self.analyze(kind)
            self.assertTrue(result["source"])
            self.assertIsInstance(result["notes"], list)
            self.assertFalse(result["automation"]["metadata_only"])
            self.assertEqual(result["name"], "webtest")
        self.assertTrue(self.analyze("lsio")["automation"]["official_catalog"])


if __name__ == "__main__":
    unittest.main()
