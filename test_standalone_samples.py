"""Offline contract tests for copyable samples; no Azure resources are modified."""

import importlib.util
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import requests
import subprocess


ROOT = Path(__file__).parent / "samples"
SCENARIOS = {
    "project-identity": "ProjectManagedIdentity",
    "agent-identity": "AgenticIdentityToken",
    "user-identity/trusted-kb": "UserEntraToken",
    "user-identity/custom-oauth": "OAuth2",
}


def load(name, scenario):
    spec = importlib.util.spec_from_file_location(name, ROOT / scenario / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScenarioContract:
    def load(self, name):
        return load(name, self.scenario)

    def setUp(self):
        self.env = {
            "AZURE_TENANT_ID": "tenant", "FOUNDRY_PROJECT_ENDPOINT": "https://project.test/api/projects/demo",
            "FOUNDRY_PROJECT_RESOURCE_ID": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/acct/projects/demo",
            "CONNECTION_NAME": "connection", "TOOLBOX_NAME": "toolbox",
            "MCP_SERVER_URL": "https://search.test/knowledgebases/kb/mcp?api-version=2026-05-01-preview",
            "AGENT_NAME": "agent", "AGENT_VERSION": "7", "QUESTION": "nonsensitive question",
        }

    def test_managed_connections_and_sdk_tool_payload(self):
        if SCENARIOS[self.scenario] == "OAuth2":
            self.skipTest("OAuth uses the supported azd connection command")
        module = self.load("provision_toolbox")
        mode = SCENARIOS[self.scenario]
        for ignored_mode in ("OAuth2", "wrong-mode"):
            with self.subTest(ignored_mode=ignored_mode), patch.dict(os.environ, {**self.env, "TOOL_AUTH_MODE": ignored_mode}, clear=True), \
                    patch.object(module, "AzureCliCredential") as credential, \
                    patch.object(module, "AIProjectClient") as client, \
                    patch.object(module.requests, "put") as put, patch("builtins.print"):
                project = client.return_value.__enter__.return_value
                project.toolboxes.create_version.return_value.version = "3"
                module.main()
                credential.return_value.get_token.assert_called_once_with("https://management.azure.com/.default")
                payload = put.call_args.kwargs["json"]["properties"]
                self.assertEqual(payload["authType"], mode)
                self.assertEqual(payload["target"], self.env["MCP_SERVER_URL"])
                self.assertEqual(payload["audience"], "https://search.azure.com")
                self.assertFalse(payload["isSharedToAll"])
                self.assertTrue(put.call_args.args[0].endswith("?api-version=2025-10-01-preview"))
                tool = project.toolboxes.create_version.call_args.kwargs["tools"][0].as_dict()
                self.assertEqual(tool["type"], "mcp")
                self.assertEqual(tool["project_connection_id"], self.env["FOUNDRY_PROJECT_RESOURCE_ID"] + "/connections/connection")
                self.assertEqual(tool["require_approval"], "never")
                project.toolboxes.update.assert_called_once_with(name="toolbox", default_version="3")

    def test_arm_error_prevents_toolbox_publication(self):
        if SCENARIOS[self.scenario] == "OAuth2":
            self.skipTest("OAuth uses the supported azd connection command")
        module = self.load("provision_toolbox")
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(module, "AzureCliCredential"), patch.object(module, "AIProjectClient") as client, \
                patch.object(module.requests, "put") as put:
            put.return_value.raise_for_status.side_effect = requests.HTTPError("403 forbidden")
            with self.assertRaises(requests.HTTPError):
                module.main()
            client.assert_not_called()

    def test_oauth_cli_contract_and_secret_redaction(self):
        if SCENARIOS[self.scenario] != "OAuth2":
            self.skipTest("Managed connection does not use OAuth")
        module = self.load("provision_toolbox")
        oauth = {**self.env, "OAUTH_CLIENT_ID": "client",
                 "OAUTH_CLIENT_SECRET": "test-only-secret", "OAUTH_SCOPE": "api://api/access_as_user"}
        with patch.dict(os.environ, oauth, clear=True), patch.object(module, "AzureCliCredential"), \
                patch.object(module.shutil, "which", return_value="azd"), \
                patch.object(module.subprocess, "run") as run, patch.object(module.requests, "get") as get, \
                patch.object(module, "AIProjectClient") as client, patch("builtins.print"):
            run.return_value = MagicMock(returncode=0)
            get.return_value.json.return_value = {"properties": {"redirectUrl": "https://callback.test"}}
            module.main()
            args = run.call_args.args[0]
            self.assertEqual(args[args.index("--auth-type") + 1], "oauth2")
            self.assertEqual(args[args.index("--client-id") + 1], "client")
            self.assertEqual(args[args.index("--project-endpoint") + 1], self.env["FOUNDRY_PROJECT_ENDPOINT"])
            project = client.return_value.__enter__.return_value
            tool = project.toolboxes.create_version.call_args.kwargs["tools"][0].as_dict()
            self.assertEqual(tool["project_connection_id"],
                             self.env["FOUNDRY_PROJECT_RESOURCE_ID"] + "/connections/connection")
            self.assertEqual(tool["server_label"], "custom_probe")
            self.assertEqual(tool["require_approval"], "never")
            self.assertNotIn("test-only-secret", tool.values())
            self.assertEqual(args[args.index("--scopes") + 1], "api://api/access_as_user offline_access")
            self.assertEqual(args[args.index("--authorization-url") + 1],
                             "https://login.microsoftonline.com/tenant/oauth2/v2.0/authorize")
            run.return_value = MagicMock(returncode=1, stdout="", stderr="failure test-only-secret")
            with self.assertRaisesRegex(RuntimeError, "failure <redacted>"):
                module.main()
            run.side_effect = subprocess.TimeoutExpired(args, 240)
            with self.assertRaisesRegex(RuntimeError, "timed out") as error:
                module.main()
            self.assertNotIn("test-only-secret", str(error.exception))

    def invoke(self, result, *, http_error=False, wrong_version=False):
        module = self.load("invoke_hosted")
        with patch.dict(os.environ, self.env, clear=True), patch.object(module, "AzureCliCredential") as credential, \
                patch.object(module, "AIProjectClient") as client, \
                patch.object(module.requests, "post") as post, patch("builtins.print"):
            project = client.return_value.__enter__.return_value
            project.agents.create_session.return_value.agent_session_id = "session"
            project.agents.get_session.return_value.version_indicator.agent_version = "8" if wrong_version else "7"
            post.return_value.json.return_value = result
            if http_error:
                post.return_value.raise_for_status.side_effect = requests.HTTPError("401 unauthorized")
            module.main()
            credential.return_value.get_token.assert_called_once_with("https://ai.azure.com/.default")
            indicator = project.agents.create_session.call_args.kwargs["version_indicator"].as_dict()
            self.assertEqual(indicator["agent_version"], "7")
            body = post.call_args.kwargs["json"]
            self.assertEqual(body["agent_session_id"], "session")
            self.assertFalse(body["store"])
            self.assertFalse(body["stream"])
            project.agents.update_details.assert_not_called()

    def test_invocation_session_and_scope(self):
        self.invoke({"status": "completed", "agent_session_id": "session", "output": []})

    def test_http_and_session_errors(self):
        result = {"status": "completed", "agent_session_id": "session", "output": []}
        with self.assertRaises(requests.HTTPError):
            self.invoke(result, http_error=True)
        with self.assertRaisesRegex(RuntimeError, "session"):
            self.invoke(result, wrong_version=True)

    def test_tool_and_consent_errors(self):
        for item in (
            {"type": "mcp_call", "error": {"code": "forbidden"}},
            {"type": "function_call_output", "output": "Error: downstream failed"},
            {"type": "function_call_output", "output": '{"error":{"http_status":403}}'},
            {"type": "mcp_call", "isError": True},
            {"type": "mcp_call", "status": "failed"},
            {"type": "mcp_call", "output": {"isError": True}},
            {"type": "oauth_consent_request"},
            {"type": "mcp_approval_request"},
        ):
            with self.subTest(item=item), self.assertRaises(RuntimeError):
                self.invoke({"status": "completed", "agent_session_id": "session", "output": [item]})
        with self.assertRaises(RuntimeError):
            self.invoke({"status": "incomplete", "agent_session_id": "session", "output": []})

    def test_no_default_success_and_expected_marker(self):
        for result in (
            {"agent_session_id": "session", "output": []},
            {"status": "completed", "agent_session_id": "session", "error": "failed", "output": []},
            {"status": "completed", "agent_session_id": "wrong-session", "output": []},
        ):
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                self.invoke(result)
        self.env["EXPECTED_TEXT"] = "known-marker"
        with self.assertRaisesRegex(RuntimeError, "EXPECTED_TEXT"):
            self.invoke({"status": "completed", "agent_session_id": "session", "output": []})
        self.invoke({"status": "completed", "agent_session_id": "session",
                     "output": [{"type": "message", "content": "known-marker"}]})

    def test_consent_state_is_not_exported(self):
        result = {"status": "incomplete", "agent_session_id": "session",
                  "output": [{"type": "oauth_consent_request",
                              "consent_link": "https://region.consent.azure-apihub.net/login?data=opaque-secret-state"}]}
        with self.assertRaises(RuntimeError) as error:
            self.invoke(result)
        self.assertNotIn("opaque-secret-state", str(error.exception))
        self.assertIn("<consent-link-redacted>", str(error.exception))

    def test_hosted_entry_point(self):
        module = self.load("hosted_agent")
        with patch.dict(os.environ, {**self.env, "AZURE_AI_MODEL_DEPLOYMENT_NAME": "model",
                                     "TOOLBOX_ENDPOINT": "https://toolbox.test"}, clear=True), \
                patch.object(module, "DefaultAzureCredential") as credential, \
                patch.object(module, "FoundryChatClient") as chat, \
                patch.object(module, "FoundryToolbox") as toolbox, \
                patch.object(module, "Agent") as agent, patch.object(module, "ResponsesHostServer") as host:
            host.return_value.run_async = AsyncMock()
            asyncio.run(module.main())
            host.return_value.run_async.assert_awaited_once()
            toolbox.assert_called_once_with(credential.return_value, name="retrieval", url="https://toolbox.test")
            self.assertEqual(chat.call_args.kwargs["model"], "model")
            self.assertEqual(agent.call_args.kwargs["default_options"], {"store": False})

    def test_copyable_files_and_identity_documentation(self):
        folder = ROOT / self.scenario
        for name in ("provision_toolbox.py", "hosted_agent.py", "invoke_hosted.py", "requirements.txt", "README.md"):
            self.assertTrue((folder / name).is_file())
        provision = (folder / "provision_toolbox.py").read_text()
        self.assertNotIn("TOOL_AUTH_MODE", provision)
        for source in folder.glob("*.py"):
            self.assertNotIn("from common import", source.read_text())
        readme = (folder / "README.md").read_text()
        self.assertIn("Data principal:", readme)
        self.assertIn("FOUNDRY_PROJECT_RESOURCE_ID", readme)
        self.assertIn("AGENT_VERSION", readme)
        if SCENARIOS[self.scenario] == "OAuth2":
            original = Path(__file__).parent / "custom-mcp"
            self.assertEqual((folder / "server.py").read_bytes(), (original / "server.py").read_bytes())
            self.assertEqual((folder / "server-requirements.txt").read_bytes(),
                             (original / "requirements.txt").read_bytes())
            self.assertIn("not proven", readme)
            self.assertIn("OAuth client ID", readme)
        else:
            self.assertIn("--assignee-object-id", readme)
            self.assertIn("--scope $env:SEARCH_RESOURCE_ID", readme)


class ProjectIdentityTests(ScenarioContract, unittest.TestCase):
    scenario = "project-identity"


class AgentIdentityTests(ScenarioContract, unittest.TestCase):
    scenario = "agent-identity"


class NativeUserIdentityTests(ScenarioContract, unittest.TestCase):
    scenario = "user-identity/trusted-kb"


class CustomOAuthIdentityTests(ScenarioContract, unittest.TestCase):
    scenario = "user-identity/custom-oauth"


if __name__ == "__main__":
    unittest.main()
