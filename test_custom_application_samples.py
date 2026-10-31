"""Offline contracts and real signed-JWT/HTTP MCP tests for custom A and B."""

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).parent
TENANT = "11111111-1111-4111-8111-111111111111"
PRINCIPAL = "22222222-2222-4222-8222-222222222222"
AUDIENCE = "33333333-3333-4333-8333-333333333333"
EXPERIMENT = "44444444-4444-4444-8444-444444444444"


def load(folder, filename):
    spec = importlib.util.spec_from_file_location(
        folder.replace("-", "_") + filename, ROOT / "samples" / folder / filename,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CustomApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def token(self, overrides=None, remove=(), key=None):
        now = int(time.time())
        claims = {
            "exp": now + 300, "iat": now, "nbf": now,
            "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
            "aud": AUDIENCE, "tid": TENANT, "oid": PRINCIPAL, "ver": "2.0",
            "idtyp": "app", "name": "never expose this", "roles": ["Mcp.Invoke"],
        }
        claims.update(overrides or {})
        for field in remove:
            claims.pop(field)
        return jwt.encode(claims, key or self.key, algorithm="RS256", headers={"kid": "test"})

    def validator(self, module):
        keys = SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=self.key.public_key()),
        )
        return module.ApplicationTokenValidator(TENANT, AUDIENCE, [PRINCIPAL], keys)

    def test_signed_jwt_allow_and_safe_claims(self):
        for folder in ("project-identity", "agent-identity"):
            with self.subTest(folder=folder):
                module = load(folder, "custom_server.py")
                validator = self.validator(module)
                result = validator.validate(self.token())
                self.assertEqual(set(result), {"tid", "oid", "aud", "iss", "ver"})
                self.assertEqual(result["oid"], PRINCIPAL)
                # ACL-based application access deliberately permits role-less tokens.
                validator.validate(self.token(remove=("roles", "idtyp")))
                with self.assertRaises(ValueError):
                    module.ApplicationTokenValidator(TENANT, AUDIENCE, [])

    def test_signed_jwt_rejections(self):
        bad_claims = [
            {"aud": "wrong"}, {"aud": [AUDIENCE, "other"]},
            {"iss": "https://issuer.invalid"}, {"exp": 1},
            {"nbf": int(time.time()) + 3600}, {"iat": int(time.time()) + 3600},
            {"tid": AUDIENCE}, {"oid": AUDIENCE}, {"oid": []}, {"ver": "1.0"},
            {"scp": "access_as_user"}, {"scp": ""}, {"idtyp": "user"},
        ]
        for folder in ("project-identity", "agent-identity"):
            validator = self.validator(load(folder, "custom_server.py"))
            for claims in bad_claims:
                with self.subTest(folder=folder, claims=claims):
                    with self.assertRaises(jwt.PyJWTError):
                        validator.validate(self.token(claims))
            for field in ("exp", "iat", "nbf", "iss", "aud", "tid", "oid", "ver"):
                with self.subTest(folder=folder, missing=field):
                    with self.assertRaises(jwt.PyJWTError):
                        validator.validate(self.token(remove=(field,)))
            with self.assertRaises(jwt.PyJWTError):
                validator.validate(self.token(key=self.wrong_key))
            with self.assertRaises(jwt.PyJWTError):
                validator.validate("not-a-jwt")
            with self.assertRaises(jwt.PyJWTError):
                validator.validate(jwt.encode({"aud": AUDIENCE}, "not-rsa", algorithm="HS256"))

    def test_http_mcp_allow_deny_and_context_isolation(self):
        async def exercise(folder):
            module = load(folder, "custom_server.py")
            app = module.create_app(self.validator(module))
            async with app.app.router.lifespan_context(app.app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://local",
                ) as client:
                    self.assertEqual((await client.get("/healthz")).status_code, 200)
                    headers = {
                        "Authorization": "Bearer " + self.token(),
                        "Accept": "application/json, text/event-stream",
                    }
                    async def rpc(method, params, request_id):
                        return await client.post("/mcp", headers=headers, json={
                            "jsonrpc": "2.0", "id": request_id,
                            "method": method, "params": params,
                        })
                    initialized = await rpc("initialize", {
                        "protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "offline-test", "version": "1"},
                    }, 1)
                    self.assertEqual(initialized.status_code, 200, initialized.text)
                    tools = await rpc("tools/list", {}, 2)
                    self.assertEqual(tools.status_code, 200, tools.text)
                    self.assertEqual(tools.json()["result"]["tools"][0]["name"], "identity_probe")
                    response = await rpc("tools/call", {
                        "name": "identity_probe", "arguments": {"experiment_id": EXPERIMENT},
                    }, 3)
                    self.assertEqual(response.status_code, 200, response.text)
                    result = response.json()["result"]
                    self.assertFalse(result.get("isError", False), result)
                    output = json.loads(result["content"][0]["text"])
                    self.assertEqual(output["claims"]["oid"], PRINCIPAL)
                    self.assertNotIn("never expose", response.text)
                    self.assertNotIn("_fastmcp", response.text)
                    invalid = await rpc("tools/call", {
                        "name": "identity_probe", "arguments": {"experiment_id": "not-a-uuid"},
                    }, 4)
                    self.assertTrue(invalid.json()["result"]["isError"])
                    for authorization in (
                        "", "Basic abc", "Bearer malformed",
                        "Bearer " + self.token({"scp": "access_as_user"}),
                        "Bearer " + self.token({"oid": AUDIENCE}),
                        "Bearer " + self.token({"exp": 1}),
                    ):
                        rejected = await client.post(
                            "/mcp", headers={"Authorization": authorization},
                            json={"jsonrpc": "2.0", "id": 5, "method": "tools/list"},
                        )
                        self.assertEqual(rejected.status_code, 401)
                        self.assertEqual(rejected.headers["www-authenticate"], "Bearer")
                    self.assertIsNone(module.IDENTITY.get())
        for folder in ("project-identity", "agent-identity"):
            with self.subTest(folder=folder):
                asyncio.run(exercise(folder))

    def test_provisioning_contracts(self):
        env = {
            "FOUNDRY_PROJECT_ENDPOINT": "https://foundry.example/api/projects/test",
            "FOUNDRY_PROJECT_RESOURCE_ID": "/subscriptions/test/projects/test",
            "AZURE_TENANT_ID": TENANT, "CONNECTION_NAME": "custom",
            "TOOLBOX_NAME": "custom-tools", "CUSTOM_MCP_SERVER_URL": "https://mcp.example/mcp",
            "CUSTOM_MCP_AUDIENCE": AUDIENCE,
        }
        for folder, auth in (
            ("project-identity", "ProjectManagedIdentity"),
            ("agent-identity", "AgenticIdentityToken"),
        ):
            module = load(folder, "provision_custom_toolbox.py")
            with patch.dict(os.environ, env, clear=True), \
                    patch.object(module, "AzureCliCredential") as credential, \
                    patch.object(module.requests, "put") as put, \
                    patch.object(module, "AIProjectClient") as project_client:
                credential.return_value.get_token.return_value.token = "arm-test-token"
                toolbox = project_client.return_value.__enter__.return_value.toolboxes
                toolbox.create_version.return_value.version = "1"
                module.main()
                properties = put.call_args.kwargs["json"]["properties"]
                self.assertEqual(properties["authType"], auth)
                self.assertEqual(properties["audience"], AUDIENCE)
                self.assertEqual(properties["target"], env["CUSTOM_MCP_SERVER_URL"])
                credential.return_value.get_token.assert_called_once_with(
                    "https://management.azure.com/.default",
                )
                put.return_value.raise_for_status.assert_called_once()
                tool = toolbox.create_version.call_args.kwargs["tools"][0]
                self.assertEqual(tool.server_url, env["CUSTOM_MCP_SERVER_URL"])
                self.assertEqual(tool.project_connection_id, env["FOUNDRY_PROJECT_RESOURCE_ID"] + "/connections/custom")
                toolbox.update.assert_called_once_with(name="custom-tools", default_version="1")
                for field, value in (
                    ("CUSTOM_MCP_SERVER_URL", "http://mcp.example/mcp"),
                    ("CUSTOM_MCP_SERVER_URL", "https://user:pass@mcp.example/mcp"),
                    ("CUSTOM_MCP_AUDIENCE", ""), ("CUSTOM_MCP_AUDIENCE", AUDIENCE + "/.default"),
                    ("CONNECTION_NAME", ""), ("TOOLBOX_NAME", "bad/name"),
                ):
                    with self.subTest(folder=folder, field=field, value=value):
                        with patch.dict(os.environ, {field: value}):
                            put.reset_mock()
                            with self.assertRaises(ValueError):
                                module.main()
                            put.assert_not_called()

    def test_copyable_servers_identical(self):
        self.assertEqual(
            (ROOT / "samples" / "project-identity" / "custom_server.py").read_bytes(),
            (ROOT / "samples" / "agent-identity" / "custom_server.py").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
