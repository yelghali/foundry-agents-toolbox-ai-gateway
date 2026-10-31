"""Cryptographic negative tests use only ephemeral keys in memory."""

import importlib.util
import os
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

os.environ["ENTRA_TENANT_ID"] = "test-tenant"
os.environ["ENTRA_AUDIENCE"] = "test-audience"
spec = importlib.util.spec_from_file_location("custom_server", Path(__file__).with_name("server.py"))
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        server.KEYS = Mock()
        server.KEYS.get_signing_key_from_jwt.return_value.key = self.key.public_key()
        now = int(time.time())
        self.claims = {
            "iss": server.ISSUER, "aud": server.AUDIENCE, "tid": server.TENANT,
            "oid": "test-user", "scp": "access_as_user", "iat": now, "nbf": now, "exp": now + 300,
        }

    def token(self, changes=None, key=None):
        return jwt.encode({**self.claims, **(changes or {})}, key or self.key, algorithm="RS256")

    def test_valid(self):
        self.assertEqual(server.validate(self.token())["oid"], "test-user")

    def test_wrong_signature(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with self.assertRaises(jwt.InvalidSignatureError):
            server.validate(self.token(key=other))

    def test_rejected_claims(self):
        for changes in (
            {"iss": "https://wrong"}, {"aud": "wrong"}, {"tid": "wrong"}, {"scp": "other"},
            {"exp": int(time.time()) - 100}, {"nbf": int(time.time()) + 100},
        ):
            with self.subTest(changes=changes), self.assertRaises(jwt.InvalidTokenError):
                server.validate(self.token(changes))

    def test_app_only_rejected(self):
        claims = self.claims.copy()
        del claims["scp"]
        with self.assertRaises(jwt.MissingRequiredClaimError):
            server.validate(jwt.encode(claims, self.key, algorithm="RS256"))

    def test_authenticated_mcp_tool_and_arguments(self):
        args = {"experiment_id": str(uuid.uuid4()), "message": "hello-toolbox", "count": 2}
        app = server.EntraBoundary(server.mcp.http_app(path="/mcp", stateless_http=True, json_response=True))
        with TestClient(app) as client:
            headers = {
                "Authorization": "Bearer " + self.token(),
                "Accept": "application/json, text/event-stream",
            }
            response = client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "probe_echo", "arguments": args},
            })
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertFalse(result.get("isError"))
        self.assertEqual(result["structuredContent"]["arguments"], args)
        self.assertEqual(result["structuredContent"]["claims"]["oid"], "test-user")

    def test_tool_discovery_omits_optional_fastmcp_metadata(self):
        app = server.EntraBoundary(server.mcp.http_app(path="/mcp", stateless_http=True, json_response=True))
        with TestClient(app) as client:
            response = client.post("/mcp", headers={
                "Authorization": "Bearer " + self.token(),
                "Accept": "application/json, text/event-stream",
            }, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(response.status_code, 200)
        tools = response.json()["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["probe_echo"])
        self.assertNotIn("_fastmcp", tools[0].get("_meta", {}))
        self.assertIn("experiment_id", tools[0]["inputSchema"]["properties"])


if __name__ == "__main__":
    unittest.main()
