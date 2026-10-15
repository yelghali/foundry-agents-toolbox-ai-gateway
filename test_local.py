"""Focused checks that do not import the hosted module's Azure startup configuration."""

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from starlette.responses import JSONResponse

import common as cm
from test_routes import backend_error, consent_challenge
from search_resources import index_body, knowledge_base_body, knowledge_source_body


def hosted_symbol(name: str, globals_: dict):
    path = cm.ROOT / "hosted" / "main.py"
    tree = ast.parse(path.read_text())
    node = next(item for item in tree.body if getattr(item, "name", None) == name)
    namespace = {"json": json, "JSONResponse": JSONResponse, **globals_}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


class NoStoreTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, body: bytes, path="/responses", method="POST"):
        captured = {}
        messages = []

        async def app(scope, receive, send):
            captured["scope"] = scope
            captured["body"] = (await receive())["body"]

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        middleware = hosted_symbol("ForceNoStore", {})(app)
        await middleware(
            {"type": "http", "method": method, "path": path,
             "headers": [(b"content-length", str(len(body)).encode()), (b"x-example", b"retained")]},
            receive, send,
        )
        return captured, messages

    async def test_overrides_storing_caller(self):
        captured, messages = await self.invoke(b'{"input":"question","store":true}')
        self.assertFalse(json.loads(captured["body"])["store"])
        self.assertEqual(dict(captured["scope"]["headers"])[b"content-length"],
                         str(len(captured["body"])).encode())
        self.assertEqual(dict(captured["scope"]["headers"])[b"x-example"], b"retained")
        self.assertEqual(messages, [])

    async def test_rejects_invalid_requests(self):
        for body, status in (
            (b"broken", 400), (b"\xff", 400), (b"[]", 400),
            (b'{"conversation":"existing"}', 400),
            (b'{"previous_response_id":"existing"}', 400),
            (b"x" * 1048577, 413),
        ):
            with self.subTest(body=body[:50]):
                captured, messages = await self.invoke(body)
                self.assertFalse(captured)
                self.assertEqual(messages[0]["status"], status)

    async def test_get_is_unchanged(self):
        captured, _ = await self.invoke(b"unchanged", method="GET")
        self.assertEqual(captured["body"], b"unchanged")

    async def test_denial_preserves_backend_status_and_principal(self):
        import base64
        import uuid

        payload = base64.urlsafe_b64encode(json.dumps({"oid": "agent-b", "aud": "Search"}).encode()).decode()
        credential = Mock()
        credential.get_token.return_value.token = f"header.{payload}.signature"
        response = httpx.Response(403, request=httpx.Request("POST", "https://example.search.windows.net/index"))
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response
        event = AsyncMock()
        retrieve = hosted_symbol("retrieve", {
            "base64": base64, "uuid": uuid, "httpx": httpx, "credential": credential, "event": event,
            "CONFIG": {"index": "index-c", "kb": "kb-c", "search_endpoint": "https://example.search.windows.net"},
        })
        with patch.object(httpx, "AsyncClient", return_value=client):
            result = json.loads(await retrieve("question", "raw"))
        self.assertEqual(result["error"]["http_status"], 403)
        self.assertEqual(result["error"]["data_principal_oid"], "agent-b")
        self.assertEqual(event.call_args.args[1]["status"], 403)


class EvidenceTests(unittest.TestCase):
    def test_classic_policies_reject_dedicated_gateway(self):
        with self.assertRaisesRegex(ValueError, "different runtime"):
            cm.standard_apim_id({
                "apimSku": "AIGateway",
                "apimResourceId": "/subscriptions/test/resourceGroups/test/providers/Microsoft.ApiManagement/aigateways/test",
            })
        resource_id = "/subscriptions/test/resourceGroups/test/providers/Microsoft.ApiManagement/service/test"
        self.assertEqual(cm.standard_apim_id({"apimSku": "StandardV2", "apimResourceId": resource_id}), resource_id)

    def test_toolbox_prompt_publication_without_classic_apim(self):
        from types import SimpleNamespace
        import publish_agents

        cohort = {
            "label": "b", "identityMode": "agent",
            "project": {"id": "/projects/b", "endpoint": "https://example.services.ai.azure.com/api/projects/b"},
            "searchId": "/search/b", "toolboxEndpoint": "https://example.services.ai.azure.com/toolbox/mcp",
            "indexMcpEndpoint": "https://example.services.ai.azure.com/index/mcp",
        }
        config = {"cohorts": [cohort], "modelDeploymentName": "lab-model", "apimResourceId": None, "apimSku": None}
        project = Mock()
        project.agents.create_version.return_value = SimpleNamespace(
            version="1", instance_identity=SimpleNamespace(principal_id="agent-b"),
        )
        with patch.object(cm, "load_config", return_value=config), patch.object(
            cm, "credential", return_value=Mock(),
        ), patch.object(cm, "connection", return_value="/connections/platform"), patch.object(
            cm, "grant",
        ), patch.object(cm, "save_config"), patch.object(
            publish_agents, "AIProjectClient", return_value=project,
        ), patch.object(publish_agents, "relay") as relay, patch(
            "sys.argv", ["publish_agents.py", "--cohort", "b", "--routes", "toolbox", "--only-agent", "prompt-b"],
        ):
            publish_agents.main()
        relay.assert_not_called()
        definition = project.agents.create_version.call_args.kwargs["definition"]
        self.assertEqual(definition.tools[0].server_url, cohort["toolboxEndpoint"])
        self.assertEqual(cohort["agents"]["prompt-b"]["versions"]["toolbox"], "1")

    def test_search_schemas_are_locally_complete(self):
        index = index_body("index-a")
        source = knowledge_source_body("ks-a", "index-a")
        kb = knowledge_base_body("kb-a", ["ks-a"], {
            "foundryOpenAIEndpoint": "https://example.openai.azure.com/",
            "modelDeploymentName": "lab-model",
        })
        self.assertEqual([field["name"] for field in index["fields"]], ["id", "title", "content"])
        self.assertEqual(source["searchIndexParameters"]["semanticConfigurationName"],
                         index["semantic"]["configurations"][0]["name"])
        self.assertEqual(source["searchIndexParameters"]["searchIndexName"], index["name"])
        self.assertEqual(kb["knowledgeSources"], [{"name": "ks-a"}])
        self.assertEqual(kb["models"][0]["azureOpenAIParameters"]["deploymentId"], "lab-model")
        self.assertNotIn("apiKey", kb["models"][0]["azureOpenAIParameters"])

    def test_role_grant_is_stable_and_preserves_scope(self):
        config = {"subscriptionId": "subscription"}
        scope = "/subscriptions/subscription/resourceGroups/lab/providers/Microsoft.Search/searchServices/example"
        with patch.object(cm, "arm") as arm:
            first = cm.grant(config, "principal", scope, cm.SEARCH_INDEX_DATA_READER_ROLE_ID)
            second = cm.grant(config, "principal", scope, cm.SEARCH_INDEX_DATA_READER_ROLE_ID)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith(scope + "/providers/Microsoft.Authorization/roleAssignments/"))
        self.assertEqual(arm.call_args.args[3]["properties"]["principalId"], "principal")
        self.assertEqual(arm.call_args.kwargs["version"], "2022-04-01")

    def test_standalone_source_has_no_sibling_lab_dependency(self):
        for filename in ("common.py", "publish_agents.py"):
            source = (cm.ROOT / filename).read_text()
            self.assertNotIn("foundry-iq-toolbox-rbac", source)
            self.assertNotIn("tracing-deployment.json", source)
        self.assertTrue((cm.ROOT / "policies" / "toolbox-proxy-policy.xml").is_file())

    def test_admin_model_connection_is_secret_safe_and_gateway_neutral(self):
        source = (cm.ROOT / "admin-model-connection.bicep").read_text()
        key_parameter = source.index("param gatewayRuntimeKey string")
        self.assertIn("@secure()", source[max(0, key_parameter - 250):key_parameter])
        self.assertIn("'ModelGateway'", source)
        self.assertIn("'ApiManagement'", source)
        self.assertIn("category: connectionCategory", source)
        self.assertIn("target: gatewayModelsBaseUrl", source)
        self.assertIn("authHeaderFormat: '{api_key}'", source)
        self.assertIn("output modelReference string = '${connection.name}/${modelName}'", source)
        outputs = [line for line in source.splitlines() if line.startswith("output ")]
        self.assertFalse(any("gatewayRuntimeKey" in line for line in outputs))

    def test_admin_model_smoke_uses_no_store_and_redacts_answer(self):
        source = (cm.ROOT / "smoke_admin_model_agent.py").read_text()
        tree = ast.parse(source)
        no_store_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "create"
            and any(keyword.arg == "store" and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False for keyword in node.keywords)
        ]
        self.assertEqual(len(no_store_calls), 1)
        self.assertIn("aigw-admin-models/gpt-4o-mini", source)
        self.assertIn('"x-correlation-id"', source)
        self.assertIn("Response content was validated but not printed.", source)
        self.assertNotIn("print(response.output_text", source)

    def test_diagrams_have_valid_visible_elements(self):
        import xml.etree.ElementTree as ET

        scene = json.loads((cm.ROOT / "docs" / "architecture.excalidraw").read_text())
        self.assertEqual(scene["type"], "excalidraw")
        ids = [element["id"] for element in scene["elements"]]
        self.assertEqual(len(ids), len(set(ids)))
        for element in scene["elements"]:
            if element["type"] == "text":
                self.assertGreater(element["width"], 0)
                self.assertGreater(element["height"], 0)
                self.assertEqual(element["strokeColor"], "#000000")
        root = ET.parse(cm.ROOT / "docs" / "architecture.svg").getroot()
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_actual_backend_unsupported(self):
        error = {"code": "HostedAgentNotSupported", "backend_error": {
            "code": -32099, "data": {"code": "HostedAgentNotSupported"},
        }}
        self.assertEqual(backend_error({"output": [{
            "type": "function_call_output", "output": json.dumps({"error": error}),
        }]}), error)

    def test_consent_extraction_preserves_actual_link(self):
        link = "https://logic-apis-eastus2.consent.azure-apim.net/login?data=abc%2Bxyz="
        self.assertEqual(consent_challenge({"message": "CONSENT_REQUIRED " + link})["consent_link"], link)
        self.assertIsNone(consent_challenge({"message": "403 forbidden"}))
        with self.assertRaises(RuntimeError):
            consent_challenge({"message": "CONSENT_REQUIRED https://example.com/login?data=abc"})

    def test_apim_update_concurrency_header(self):
        settings = {"subscriptionId": "test"}
        credential = Mock()
        credential.get_token.return_value.token = "test-token"
        response = Mock(content=b'{"properties":{}}')
        response.status_code = 200
        with patch.object(cm, "credential", return_value=credential), patch.object(
            cm.requests, "request", return_value=response,
        ) as request:
            cm.arm(settings, "PUT", "/providers/Microsoft.ApiManagement/service/test/apis/test")
            self.assertEqual(request.call_args.kwargs["headers"]["If-Match"], "*")
            cm.arm(settings, "PUT", "/providers/Microsoft.Search/searchServices/test")
            self.assertNotIn("If-Match", request.call_args.kwargs["headers"])

    def test_llm_denial_is_not_backend_evidence(self):
        result = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "403 forbidden"}]}]}
        self.assertIsNone(backend_error(result))

    def test_actual_structured_tool_denial(self):
        error = {"code": "authorization_denied", "http_status": 403}
        self.assertEqual(backend_error({"output": [{
            "type": "function_call_output", "output": json.dumps({"error": error}),
        }]}), error)

    def test_sanitized_failure_is_not_classified_as_forbidden(self):
        error = backend_error({"output": [{"type": "function_call_output", "output": "Error: Function failed."}]})
        self.assertNotIn("403", json.dumps(error))

    def test_cohort_save_preserves_other_project_state(self):
        with tempfile.TemporaryDirectory(prefix="abc-config-test-") as directory:
            root = Path(directory)
            (root / ".config.json").write_text(json.dumps({"cohorts": [
                {"label": "a", "version": "new-a"}, {"label": "b", "version": "old-b"},
            ]}))
            with patch.object(cm, "ROOT", root):
                cm.save_config({"cohorts": [
                    {"label": "a", "version": "stale-a"}, {"label": "b", "version": "new-b"},
                ]}, "b")
                actual = cm.load_config()
            self.assertEqual(actual["cohorts"], [
                {"label": "a", "version": "new-a"}, {"label": "b", "version": "new-b"},
            ])

    def test_config_replace_retries_windows_sharing_failure(self):
        with tempfile.TemporaryDirectory(prefix="abc-retry-test-") as directory:
            root = Path(directory)
            config = {"cohorts": [{"label": "c", "version": "old"}]}
            (root / ".config.json").write_text(json.dumps(config))
            failure = PermissionError("sharing violation")
            failure.winerror = 32
            original = cm.os.replace
            calls = 0

            def replace(source, destination):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise failure
                return original(source, destination)

            with patch.object(cm, "ROOT", root), patch.object(
                cm.os, "replace", side_effect=replace,
            ), patch.object(cm.time, "sleep"):
                cm.save_config({"cohorts": [{"label": "c", "version": "new"}]}, "c")
                self.assertEqual(cm.load_config()["cohorts"][0]["version"], "new")
            self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
