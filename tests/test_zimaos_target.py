# SPDX-License-Identifier: GPL-3.0-only
"""Isolated, non-network tests of ZimaOS address routing.

Only a handful of pure routing functions are compiled from the production
module. No Docker socket, NAS files, credentials, or HTTP network are used.
"""
import ast
import os
import types
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException


SOURCE = (Path(__file__).resolve().parents[1] / "main.py").read_text("utf-8")
NAMES = {
    "_normalized_zima_host",
    "_internal_zimaos_target",
    "_install_target",
    "_check_target",
}


LAN_ADDRESS = "http://" + ".".join(("192", "168", "1", "50"))
ENV_LAN_ADDRESS = "http://" + ".".join(("10", "0", "0", "42"))

class Payload:
    host = ""
    internal_host = ""
    totp_code = "123456"
    def __init__(self, host, internal_host="", totp_code="123456"):
        self.host = host
        self.internal_host = internal_host
        self.totp_code = totp_code
    def model_copy(self, update):
        return Payload(update["host"], self.internal_host, self.totp_code)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SOURCE)
        functions = [
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in NAMES
        ]
        self.assertEqual(len(functions), len(NAMES))
        module = ast.Module(body=functions, type_ignores=[])
        ast.fix_missing_locations(module)
        self.guards = []
        self.safe_calls = []
        self.request = types.SimpleNamespace(session={"csrf": "test-session"})

        def safe_host(value):
            self.safe_calls.append(value)
            host = urllib.parse.urlsplit(value if "://" in value else "http://" + value).hostname
            if host and host.endswith(".example.org"):
                raise HTTPException(400, "Public target rejected")
            return value if "://" in value else "http://" + value

        ns = {
            "urllib": urllib,
            "Install": Payload,
            "Request": object,
            "os": os,
            "HTTPException": HTTPException,
            "_proxy_hosts": lambda: {"im.example.org"},
            "_totp_saved": lambda: "offline-unit-test-secret",
            "_verify_totp": lambda secret, code, scope: code == "123456",
            "_proxy_guard": lambda request, payload: self.guards.append(payload.host),
            "safe_host": safe_host,
        }
        exec(compile(module, "<routing>", "exec"), ns)
        self.ns = ns

    def test_local_zimaos_address_does_not_require_proxy_or_env(self):
        with patch.dict(os.environ, {"IM_INTERNAL_ZIMAOS_URL": ""}):
            result = self.ns["_install_target"](self.request, Payload(LAN_ADDRESS))
        self.assertEqual(result.host, LAN_ADDRESS)
        self.assertEqual(self.guards, [])

    def test_local_address_cannot_bypass_required_totp(self):
        with self.assertRaises(HTTPException) as error:
            self.ns["_install_target"](
                self.request, Payload(LAN_ADDRESS, totp_code="000000")
            )
        self.assertEqual(error.exception.status_code, 403)
        self.assertIn("Authenticator-Code", error.exception.detail)

    def test_allowlisted_reverse_proxy_routes_to_entered_private_address(self):
        with patch.dict(os.environ, {"IM_INTERNAL_ZIMAOS_URL": ""}):
            result = self.ns["_install_target"](
                self.request, Payload("im.example.org", LAN_ADDRESS)
            )
            check = self.ns["_check_target"]("im.example.org", LAN_ADDRESS)
        self.assertEqual(result.host, LAN_ADDRESS)
        self.assertEqual(check, LAN_ADDRESS)
        self.assertEqual(self.guards, ["im.example.org"])

    def test_env_fallback_is_supported_for_existing_users(self):
        with patch.dict(os.environ, {"IM_INTERNAL_ZIMAOS_URL": ENV_LAN_ADDRESS}):
            result = self.ns["_install_target"](self.request, Payload("im.example.org"))
        self.assertEqual(result.host, ENV_LAN_ADDRESS)

    def test_missing_lan_address_reports_helpful_message(self):
        with patch.dict(os.environ, {"IM_INTERNAL_ZIMAOS_URL": ""}):
            with self.assertRaises(HTTPException) as cm:
                self.ns["_install_target"](self.request, Payload("im.example.org"))
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("interne ZimaOS-Adresse", cm.exception.detail)
        self.assertIn("NAS-LAN-IP", cm.exception.detail)

    def test_proxy_domain_rejected_as_internal_address(self):
        with patch.dict(os.environ, {"IM_INTERNAL_ZIMAOS_URL": ""}):
            with self.assertRaises(HTTPException) as cm:
                self.ns["_install_target"](
                    None, Payload("im.example.org", "https://im.example.org")
                )
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("Reverse-Proxy-Domain", cm.exception.detail)

    def test_public_internal_address_never_used_as_api_target(self):
        with patch.dict(os.environ, {"IM_INTERNAL_ZIMAOS_URL": ""}):
            with self.assertRaises(HTTPException) as cm:
                self.ns["_install_target"](
                    None, Payload("im.example.org", "https://other.example.org")
                )
        self.assertEqual(cm.exception.status_code, 400)

    def test_request_mapping_does_not_modify_input(self):
        payload = Payload("im.example.org", LAN_ADDRESS)
        self.ns["_install_target"](self.request, payload)
        self.assertEqual(payload.host, "im.example.org")
        self.assertEqual(payload.internal_host, LAN_ADDRESS)


if __name__ == "__main__":
    unittest.main()
